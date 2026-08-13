import os
import time


class RunCompletionTracker:
    """Tracks whether a KovaaK's run just finished, so the overlay can show
    only around the results screen instead of the whole time you're not
    actively aiming (which also includes menus, scenario browsing, etc).

    KovaaK's writes a .perf file to its "performances" folder the instant a
    run ends - real installs can have several thousand of these, so this
    avoids rescanning the whole folder on every check: a plain entry count
    (no stat() calls) gates whether a full mtime scan is needed, and checks
    are throttled to once a second in steady state. Call force_recheck()
    right when aiming stops, so a just-completed run doesn't sit stale for
    up to that full second before the overlay reacts.

    RESULTS_VISIBLE_SECONDS is a fallback ceiling for if you never touch a
    trigger button (Play/Next/Replay) at all - the primary way this window
    ends is the caller calling dismiss() when a click lands in one of those
    calibrated zones, which is far more precise than any fixed timeout.
    """

    RESULTS_VISIBLE_SECONDS = 60
    CHECK_INTERVAL_SECONDS = 1.0
    # Caps how much of the visible-results budget a single gap between
    # should_show_results() calls can consume. Normal polling ticks every
    # ~50ms, so a gap bigger than this means the caller wasn't calling in
    # (covered by another window, or actively aiming) rather than genuine
    # elapsed viewing time - e.g. alt-tabbing away for 10s and back
    # shouldn't silently burn the whole budget while you're gone.
    MAX_TICK_SECONDS = 0.5

    def __init__(self):
        self._perf_dir = None
        self._last_checked = 0.0
        self._last_seen_count = None
        self._newest_file_mtime = 0.0
        self._results_remaining = 0.0
        self._last_tick = None

    def set_perf_dir(self, perf_dir):
        if perf_dir == self._perf_dir:
            return
        self._perf_dir = perf_dir
        self._last_checked = 0.0
        self._last_seen_count = None
        self._results_remaining = 0.0
        self._last_tick = None
        # Baseline against the actual newest existing file, not a
        # time.time() guess, so a genuinely new file's mtime is
        # unambiguously later rather than racing a wall-clock timestamp.
        self._newest_file_mtime = self._scan_newest_mtime()

    def force_recheck(self):
        """Bypass the steady-state throttle for the very next check."""
        self._last_checked = 0.0

    def dismiss(self):
        """End the visible window immediately - call when a click lands in
        a calibrated trigger zone (Play/Next/Replay/scenario list)."""
        self._results_remaining = 0.0

    def _scan_newest_mtime(self):
        try:
            return max(
                (entry.stat().st_mtime for entry in os.scandir(self._perf_dir) if entry.is_file()),
                default=0.0,
            )
        except OSError:
            return 0.0

    def _count_entries(self):
        try:
            return sum(1 for entry in os.scandir(self._perf_dir) if entry.is_file())
        except OSError:
            return None

    def _check_for_new_completion(self):
        if not self._perf_dir:
            return
        now = time.time()
        if now - self._last_checked < self.CHECK_INTERVAL_SECONDS:
            return
        self._last_checked = now

        count = self._count_entries()
        if count is None or count == self._last_seen_count:
            return
        self._last_seen_count = count

        newest = self._scan_newest_mtime()
        if newest > self._newest_file_mtime:
            self._newest_file_mtime = newest
            self._results_remaining = self.RESULTS_VISIBLE_SECONDS

    def should_show_results(self):
        """True for a window right after a run completes, until dismiss()
        is called or the fallback timeout runs out. If the performances
        folder couldn't be located at all, fails toward True (show
        whenever not aiming) so a detection failure never means the score
        goes unprotected."""
        if not self._perf_dir:
            return True

        now = time.time()
        if self._last_tick is not None and self._results_remaining > 0:
            elapsed = min(now - self._last_tick, self.MAX_TICK_SECONDS)
            self._results_remaining = max(0.0, self._results_remaining - elapsed)
        self._last_tick = now

        self._check_for_new_completion()
        return self._results_remaining > 0
