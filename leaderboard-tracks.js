(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.NATUREBENCH_TRACKS = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  const TRACKS = Object.freeze({
    full: Object.freeze({
      key: "full",
      label: "Full",
      title: "Full benchmark",
      taskCount: 90,
      caseIds: null,
      summaryNote: "Primary NatureBench track",
      description: "All 90 NatureBench tasks for full-benchmark performance reporting.",
    }),
    "naturebench-25": Object.freeze({
      key: "naturebench-25",
      label: "NatureBench-25",
      title: "NatureBench-25",
      taskCount: 25,
      caseIds: Object.freeze([
        "s41467-025-63418-x",
        "s41587-024-02414-w",
        "s41587-024-02428-4",
        "s41592-022-01709-7",
        "s41592-023-02124-2",
        "s41592-024-02316-4",
        "s41592-025-02662-x",
        "s41592-025-02665-8",
        "s41592-025-02776-2",
        "s41592-025-02924-8",
        "s41592-025-02983-x",
        "s42256-022-00447-x",
        "s42256-022-00541-0",
        "s42256-023-00627-3",
        "s42256-023-00628-2",
        "s42256-023-00630-8",
        "s42256-023-00639-z",
        "s42256-023-00654-0",
        "s42256-024-00790-1",
        "s42256-024-00892-w",
        "s42256-025-01042-6",
        "s43588-024-00698-1",
        "s43588-024-00733-1",
        "s43588-025-00903-9",
        "s43588-025-00917-3",
      ]),
      summaryNote: "Official 25-task track",
      description: "A 25-task subset for lower-cost evaluation and faster iteration.",
    }),
  });

  function mean(values) {
    if (!values.length) return null;
    return values.reduce((total, value) => total + value, 0) / values.length;
  }

  function median(values) {
    if (!values.length) return null;
    const ordered = [...values].sort((left, right) => left - right);
    const midpoint = Math.floor(ordered.length / 2);
    if (ordered.length % 2) return ordered[midpoint];
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2;
  }

  function casesForTrack(data, trackKey) {
    const track = TRACKS[trackKey];
    if (!track) throw new Error(`Unknown leaderboard track: ${trackKey}`);

    const caseIds = track.caseIds ? new Set(track.caseIds) : null;
    const cases = caseIds
      ? data.cases.filter((item) => caseIds.has(item.caseId))
      : [...data.cases];
    if (cases.length !== track.taskCount) {
      throw new Error(
        `${track.label} expected ${track.taskCount} tasks, found ${cases.length}`,
      );
    }
    return cases;
  }

  function metricsForModel(modelName, cases) {
    const scores = cases.map((item) => {
      const score = item.scores[modelName];
      if (!score) throw new Error(`Missing ${modelName} score for ${item.caseId}`);
      return score;
    });
    const validScores = scores
      .filter((score) => score.state === "valid" && Number.isFinite(score.value))
      .map((score) => Number(score.value));
    const allScores = scores.map((score) => (
      score.state === "valid" && Number.isFinite(score.value)
        ? Number(score.value)
        : -1
    ));
    const invalid = scores.filter((score) => score.state === "invalid").length;
    const scored = scores.filter((score) => score.state !== "none").length;
    const matchCount = validScores.filter((value) => value >= 0).length;
    const surpassCount = validScores.filter((value) => value > 0.1).length;
    const total = cases.length;

    return {
      invalid,
      matchCount,
      surpassCount,
      validCount: validScores.length,
      scoredCount: scored,
      matchSota: (matchCount / total) * 100,
      surpassSota: (surpassCount / total) * 100,
      meanAll: mean(allScores),
      medianAll: median(allScores),
      medianValid: median(validScores),
      completionRate: (validScores.length / total) * 100,
      scoreRate: (scored / total) * 100,
    };
  }

  function buildTrackLeaderboard(data, trackKey) {
    const cases = casesForTrack(data, trackKey);
    return data.leaderboard.map((row) => ({
      ...row,
      ...metricsForModel(row.name, cases),
      track: trackKey,
    }));
  }

  function rankLeaderboard(rows) {
    const ordered = [...rows].sort((left, right) => (
      right.surpassCount - left.surpassCount
      || right.matchCount - left.matchCount
    ));
    let previousKey = "";
    let rank = 0;
    return ordered.map((row, index) => {
      const key = `${row.surpassCount}:${row.matchCount}`;
      if (key !== previousKey) {
        rank = index + 1;
        previousKey = key;
      }
      return { ...row, rank };
    });
  }

  return Object.freeze({
    TRACKS,
    buildTrackLeaderboard,
    casesForTrack,
    rankLeaderboard,
  });
});
