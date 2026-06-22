window.NATUREBENCH_DATA = {
  "benchmark": {
    "taskCount": 90,
    "modelCount": 10,
    "domainCount": 6
  },
  "models": [
    {
      "name": "Opus 4.6"
    },
    {
      "name": "GPT-5.4"
    },
    {
      "name": "Kimi K2.6"
    },
    {
      "name": "MiniMax-M2.7"
    },
    {
      "name": "DeepSeek-V4-Pro"
    },
    {
      "name": "GLM-5.1"
    },
    {
      "name": "Gemini 3.5 Flash"
    },
    {
      "name": "Qwen 3.7 Max"
    },
    {
      "name": "GPT-5.5"
    },
    {
      "name": "Opus 4.7"
    }
  ],
  "leaderboard": [
    {
      "name": "Opus 4.7",
      "harness": "Claude Code",
      "invalid": 0,
      "matchSota": 47.7778,
      "surpassSota": 17.7778,
      "strongSurpassSota": 3.3333,
      "meanAll": -4.5376,
      "medianAll": -0.007,
      "medianValid": -0.007,
      "completionRate": 100,
      "scoreRate": 100
    },
    {
      "name": "Gemini 3.5 Flash",
      "harness": "Gemini CLI",
      "invalid": 4,
      "matchSota": 37.7778,
      "surpassSota": 15.5556,
      "strongSurpassSota": 3.3333,
      "meanAll": -5.7054,
      "medianAll": -0.0829,
      "medianValid": -0.0411,
      "completionRate": 94.4444,
      "scoreRate": 98.8889
    },
    {
      "name": "GPT-5.5",
      "harness": "Codex",
      "invalid": 13,
      "matchSota": 44.4444,
      "surpassSota": 14.4444,
      "strongSurpassSota": 3.3333,
      "meanAll": -2.8113,
      "medianAll": -0.0549,
      "medianValid": 0.0008,
      "completionRate": 84.4444,
      "scoreRate": 98.8889
    },
    {
      "name": "Opus 4.6",
      "harness": "Claude Code",
      "invalid": 0,
      "matchSota": 36.6667,
      "surpassSota": 12.2222,
      "strongSurpassSota": 1.1111,
      "meanAll": -2.015,
      "medianAll": -0.0608,
      "medianValid": -0.0608,
      "completionRate": 100,
      "scoreRate": 100
    },
    {
      "name": "Qwen 3.7 Max",
      "harness": "Claude Code",
      "invalid": 3,
      "matchSota": 28.8889,
      "surpassSota": 10,
      "strongSurpassSota": 2.2222,
      "meanAll": -2.9383,
      "medianAll": -0.1214,
      "medianValid": -0.1049,
      "completionRate": 95.5556,
      "scoreRate": 98.8889
    },
    {
      "name": "Kimi K2.6",
      "harness": "Claude Code",
      "invalid": 2,
      "matchSota": 30,
      "surpassSota": 8.8889,
      "strongSurpassSota": 2.2222,
      "meanAll": -10.1106,
      "medianAll": -0.1423,
      "medianValid": -0.0865,
      "completionRate": 92.2222,
      "scoreRate": 94.4444
    },
    {
      "name": "GPT-5.4",
      "harness": "Codex",
      "invalid": 5,
      "matchSota": 27.7778,
      "surpassSota": 8.8889,
      "strongSurpassSota": 0,
      "meanAll": -3.7164,
      "medianAll": -0.1234,
      "medianValid": -0.1129,
      "completionRate": 94.4444,
      "scoreRate": 100
    },
    {
      "name": "GLM-5.1",
      "harness": "Claude Code",
      "invalid": 0,
      "matchSota": 28.8889,
      "surpassSota": 7.7778,
      "strongSurpassSota": 1.1111,
      "meanAll": -8.4442,
      "medianAll": -0.1503,
      "medianValid": -0.1305,
      "completionRate": 93.3333,
      "scoreRate": 93.3333
    },
    {
      "name": "DeepSeek-V4-Pro",
      "harness": "Claude Code",
      "invalid": 0,
      "matchSota": 26.6667,
      "surpassSota": 4.4444,
      "strongSurpassSota": 1.1111,
      "meanAll": -8.571,
      "medianAll": -0.2421,
      "medianValid": -0.2389,
      "completionRate": 98.8889,
      "scoreRate": 98.8889
    },
    {
      "name": "MiniMax-M2.7",
      "harness": "Claude Code",
      "invalid": 5,
      "matchSota": 13.3333,
      "surpassSota": 1.1111,
      "strongSurpassSota": 0,
      "meanAll": -11.7616,
      "medianAll": -0.4007,
      "medianValid": -0.3471,
      "completionRate": 93.3333,
      "scoreRate": 98.8889
    }
  ],
  "distributions": [
    {
      "name": "Opus 4.7",
      "bins": [
        {
          "label": "none/invalid",
          "count": 0,
          "percent": 0
        },
        {
          "label": "g < -0.5",
          "count": 11,
          "percent": 12.2
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 36,
          "percent": 40
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 27,
          "percent": 30
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 13,
          "percent": 14.4
        },
        {
          "label": "g > 0.5",
          "count": 3,
          "percent": 3.3
        }
      ]
    },
    {
      "name": "Gemini 3.5 Flash",
      "bins": [
        {
          "label": "none/invalid",
          "count": 5,
          "percent": 5.6
        },
        {
          "label": "g < -0.5",
          "count": 14,
          "percent": 15.6
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 37,
          "percent": 41.1
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 20,
          "percent": 22.2
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 11,
          "percent": 12.2
        },
        {
          "label": "g > 0.5",
          "count": 3,
          "percent": 3.3
        }
      ]
    },
    {
      "name": "GPT-5.5",
      "bins": [
        {
          "label": "none/invalid",
          "count": 14,
          "percent": 15.6
        },
        {
          "label": "g < -0.5",
          "count": 7,
          "percent": 7.8
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 29,
          "percent": 32.2
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 27,
          "percent": 30
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 10,
          "percent": 11.1
        },
        {
          "label": "g > 0.5",
          "count": 3,
          "percent": 3.3
        }
      ]
    },
    {
      "name": "Opus 4.6",
      "bins": [
        {
          "label": "none/invalid",
          "count": 0,
          "percent": 0
        },
        {
          "label": "g < -0.5",
          "count": 16,
          "percent": 17.8
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 41,
          "percent": 45.6
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 22,
          "percent": 24.4
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 10,
          "percent": 11.1
        },
        {
          "label": "g > 0.5",
          "count": 1,
          "percent": 1.1
        }
      ]
    },
    {
      "name": "Qwen 3.7 Max",
      "bins": [
        {
          "label": "none/invalid",
          "count": 4,
          "percent": 4.4
        },
        {
          "label": "g < -0.5",
          "count": 19,
          "percent": 21.1
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 41,
          "percent": 45.6
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 17,
          "percent": 18.9
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 7,
          "percent": 7.8
        },
        {
          "label": "g > 0.5",
          "count": 2,
          "percent": 2.2
        }
      ]
    },
    {
      "name": "Kimi K2.6",
      "bins": [
        {
          "label": "none/invalid",
          "count": 7,
          "percent": 7.8
        },
        {
          "label": "g < -0.5",
          "count": 21,
          "percent": 23.3
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 35,
          "percent": 38.9
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 19,
          "percent": 21.1
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 6,
          "percent": 6.7
        },
        {
          "label": "g > 0.5",
          "count": 2,
          "percent": 2.2
        }
      ]
    },
    {
      "name": "GPT-5.4",
      "bins": [
        {
          "label": "none/invalid",
          "count": 5,
          "percent": 5.6
        },
        {
          "label": "g < -0.5",
          "count": 22,
          "percent": 24.4
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 38,
          "percent": 42.2
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 17,
          "percent": 18.9
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 8,
          "percent": 8.9
        },
        {
          "label": "g > 0.5",
          "count": 0,
          "percent": 0
        }
      ]
    },
    {
      "name": "GLM-5.1",
      "bins": [
        {
          "label": "none/invalid",
          "count": 6,
          "percent": 6.7
        },
        {
          "label": "g < -0.5",
          "count": 19,
          "percent": 21.1
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 39,
          "percent": 43.3
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 19,
          "percent": 21.1
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 6,
          "percent": 6.7
        },
        {
          "label": "g > 0.5",
          "count": 1,
          "percent": 1.1
        }
      ]
    },
    {
      "name": "DeepSeek-V4-Pro",
      "bins": [
        {
          "label": "none/invalid",
          "count": 1,
          "percent": 1.1
        },
        {
          "label": "g < -0.5",
          "count": 26,
          "percent": 28.9
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 39,
          "percent": 43.3
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 20,
          "percent": 22.2
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 3,
          "percent": 3.3
        },
        {
          "label": "g > 0.5",
          "count": 1,
          "percent": 1.1
        }
      ]
    },
    {
      "name": "MiniMax-M2.7",
      "bins": [
        {
          "label": "none/invalid",
          "count": 6,
          "percent": 6.7
        },
        {
          "label": "g < -0.5",
          "count": 35,
          "percent": 38.9
        },
        {
          "label": "-0.5 <= g < 0",
          "count": 37,
          "percent": 41.1
        },
        {
          "label": "0 <= g <= 0.1",
          "count": 11,
          "percent": 12.2
        },
        {
          "label": "0.1 < g <= 0.5",
          "count": 1,
          "percent": 1.1
        },
        {
          "label": "g > 0.5",
          "count": 0,
          "percent": 0
        }
      ]
    }
  ],
  "domains": [
    {
      "domain": "Cellular Omics",
      "n": 31,
      "winner": "GPT-5.5",
      "winnerSurpassSota": 25.8065,
      "winnerMatchSota": 54.8387,
      "winnerMedianAll": 0.0029,
      "models": [
        {
          "name": "GPT-5.5",
          "surpassSota": 25.8065
        },
        {
          "name": "Gemini 3.5 Flash",
          "surpassSota": 25.8065
        },
        {
          "name": "Opus 4.7",
          "surpassSota": 22.5806
        },
        {
          "name": "Opus 4.6",
          "surpassSota": 19.3548
        },
        {
          "name": "Qwen 3.7 Max",
          "surpassSota": 16.129
        },
        {
          "name": "GLM-5.1",
          "surpassSota": 12.9032
        },
        {
          "name": "Kimi K2.6",
          "surpassSota": 12.9032
        },
        {
          "name": "GPT-5.4",
          "surpassSota": 12.9032
        },
        {
          "name": "DeepSeek-V4-Pro",
          "surpassSota": 9.6774
        },
        {
          "name": "MiniMax-M2.7",
          "surpassSota": 3.2258
        }
      ]
    },
    {
      "domain": "Protein Biology",
      "n": 16,
      "winner": "Opus 4.7",
      "winnerSurpassSota": 12.5,
      "winnerMatchSota": 56.25,
      "winnerMedianAll": 0.0114,
      "models": [
        {
          "name": "Opus 4.7",
          "surpassSota": 12.5
        },
        {
          "name": "Kimi K2.6",
          "surpassSota": 12.5
        },
        {
          "name": "Qwen 3.7 Max",
          "surpassSota": 12.5
        },
        {
          "name": "Opus 4.6",
          "surpassSota": 12.5
        },
        {
          "name": "GPT-5.5",
          "surpassSota": 6.25
        },
        {
          "name": "Gemini 3.5 Flash",
          "surpassSota": 6.25
        },
        {
          "name": "DeepSeek-V4-Pro",
          "surpassSota": 6.25
        },
        {
          "name": "GPT-5.4",
          "surpassSota": 6.25
        },
        {
          "name": "GLM-5.1",
          "surpassSota": 6.25
        },
        {
          "name": "MiniMax-M2.7",
          "surpassSota": 0
        }
      ]
    },
    {
      "domain": "Biomedical Modeling",
      "n": 14,
      "winner": "GPT-5.5",
      "winnerSurpassSota": 7.1429,
      "winnerMatchSota": 35.7143,
      "winnerMedianAll": -0.1247,
      "models": [
        {
          "name": "GPT-5.5",
          "surpassSota": 7.1429
        },
        {
          "name": "Opus 4.7",
          "surpassSota": 7.1429
        },
        {
          "name": "GLM-5.1",
          "surpassSota": 7.1429
        },
        {
          "name": "Gemini 3.5 Flash",
          "surpassSota": 7.1429
        },
        {
          "name": "Opus 4.6",
          "surpassSota": 0
        },
        {
          "name": "Kimi K2.6",
          "surpassSota": 0
        },
        {
          "name": "Qwen 3.7 Max",
          "surpassSota": 0
        },
        {
          "name": "MiniMax-M2.7",
          "surpassSota": 0
        },
        {
          "name": "GPT-5.4",
          "surpassSota": 0
        },
        {
          "name": "DeepSeek-V4-Pro",
          "surpassSota": 0
        }
      ]
    },
    {
      "domain": "Physical Modeling",
      "n": 13,
      "winner": "Opus 4.7",
      "winnerSurpassSota": 30.7692,
      "winnerMatchSota": 46.1538,
      "winnerMedianAll": -0.0505,
      "models": [
        {
          "name": "Opus 4.7",
          "surpassSota": 30.7692
        },
        {
          "name": "Gemini 3.5 Flash",
          "surpassSota": 30.7692
        },
        {
          "name": "GPT-5.5",
          "surpassSota": 23.0769
        },
        {
          "name": "Opus 4.6",
          "surpassSota": 23.0769
        },
        {
          "name": "GPT-5.4",
          "surpassSota": 23.0769
        },
        {
          "name": "Qwen 3.7 Max",
          "surpassSota": 15.3846
        },
        {
          "name": "Kimi K2.6",
          "surpassSota": 15.3846
        },
        {
          "name": "GLM-5.1",
          "surpassSota": 7.6923
        },
        {
          "name": "DeepSeek-V4-Pro",
          "surpassSota": 0
        },
        {
          "name": "MiniMax-M2.7",
          "surpassSota": 0
        }
      ]
    },
    {
      "domain": "Molecular Design",
      "n": 11,
      "winner": "Opus 4.7",
      "winnerSurpassSota": 18.1818,
      "winnerMatchSota": 45.4545,
      "winnerMedianAll": -0.0934,
      "models": [
        {
          "name": "Opus 4.7",
          "surpassSota": 18.1818
        },
        {
          "name": "Opus 4.6",
          "surpassSota": 0
        },
        {
          "name": "Kimi K2.6",
          "surpassSota": 0
        },
        {
          "name": "Gemini 3.5 Flash",
          "surpassSota": 0
        },
        {
          "name": "GPT-5.4",
          "surpassSota": 0
        },
        {
          "name": "GLM-5.1",
          "surpassSota": 0
        },
        {
          "name": "GPT-5.5",
          "surpassSota": 0
        },
        {
          "name": "DeepSeek-V4-Pro",
          "surpassSota": 0
        },
        {
          "name": "Qwen 3.7 Max",
          "surpassSota": 0
        },
        {
          "name": "MiniMax-M2.7",
          "surpassSota": 0
        }
      ]
    },
    {
      "domain": "Relational Reasoning",
      "n": 5,
      "winner": "Opus 4.7",
      "winnerSurpassSota": 0,
      "winnerMatchSota": 60,
      "winnerMedianAll": 0.0128,
      "models": [
        {
          "name": "Opus 4.7",
          "surpassSota": 0
        },
        {
          "name": "GPT-5.5",
          "surpassSota": 0
        },
        {
          "name": "Opus 4.6",
          "surpassSota": 0
        },
        {
          "name": "Gemini 3.5 Flash",
          "surpassSota": 0
        },
        {
          "name": "Kimi K2.6",
          "surpassSota": 0
        },
        {
          "name": "DeepSeek-V4-Pro",
          "surpassSota": 0
        },
        {
          "name": "GPT-5.4",
          "surpassSota": 0
        },
        {
          "name": "GLM-5.1",
          "surpassSota": 0
        },
        {
          "name": "Qwen 3.7 Max",
          "surpassSota": 0
        },
        {
          "name": "MiniMax-M2.7",
          "surpassSota": 0
        }
      ]
    }
  ],
  "cases": [
    {
      "caseId": "s41467-025-63412-3",
      "title": "Lasso Peptide Property Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Opus 4.6",
      "bestScore": 0.101586,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.101586
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.079069
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.096415
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.016465
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.026994
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.051191
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.097026
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.011682
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.097818
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.076536
        }
      }
    },
    {
      "caseId": "s41467-025-63418-x",
      "title": "Spatial Multi-Omics Domain Identification",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part2",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.054332,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.094636
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.229845
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.213791
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.271908
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.4714
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.020829
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.054332
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.066317
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.268628
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.004816
        }
      }
    },
    {
      "caseId": "s41467-025-64512-w",
      "title": "Protein-Protein Interaction Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Classification",
      "taskDir": "part1",
      "bestModel": "Opus 4.7",
      "bestScore": 0.00906,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.018044
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.400178
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.235832
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.40564
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.238852
        },
        "GLM-5.1": {
          "state": "none",
          "value": null
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.215454
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.081813
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.192397
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.00906
        }
      }
    },
    {
      "caseId": "s41467-025-65557-7",
      "title": "Spatial Clustering of Single-Molecule Localization Point Clouds",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": 0.301107,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.007642
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.028632
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.020095
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.034181
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.035529
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.002909
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.030056
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.014237
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.000487
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.301107
        }
      }
    },
    {
      "caseId": "s41551-024-01257-9",
      "title": "Pulmonary Nodule Malignancy Classification from 3D CT Scans",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Classification",
      "taskDir": "buggy",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": 0.022845,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.012248
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.014134
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.019072
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.015231
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.016535
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.012762
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.005689
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.022845
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.006451
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.005209
        }
      }
    },
    {
      "caseId": "s41551-024-01312-5",
      "title": "Cancer Gene Identification on Biological Networks",
      "domain": "Cellular Omics",
      "mlTaskType": "Classification",
      "taskDir": "part1",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.196232,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.1777
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.158202
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.127772
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.082364
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.000963
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.101317
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.196232
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.13838
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.186245
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.176661
        }
      }
    },
    {
      "caseId": "s41551-025-01528-z",
      "title": "Single-Cell Transcriptome-to-Proteome Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "DeepSeek-V4-Pro",
      "bestScore": 0.018125,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.010282
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.011214
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.004965
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.050071
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.018125
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.01112
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.016978
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.00216
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.008691
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.007505
        }
      }
    },
    {
      "caseId": "s41587-024-02414-w",
      "title": "Yeast Promoter Expression Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part1",
      "bestModel": "GPT-5.5",
      "bestScore": -0.054554,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.08083
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.10491
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.165025
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.215411
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.22453
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.103428
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.08527
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.100745
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.054554
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.058151
        }
      }
    },
    {
      "caseId": "s41587-024-02428-4",
      "title": "Protein-Protein Interaction Interface Residue Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Classification",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": -0.008703,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.038816
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.121051
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.146263
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.187747
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.18424
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.097907
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.147003
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.089804
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.142087
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.008703
        }
      }
    },
    {
      "caseId": "s41587-025-02585-0",
      "title": "Multiplexed Protein Image Decompression",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Segmentation/Detection",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": -0.10968,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.172775
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.301268
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.822215
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.869659
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.774346
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.643424
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.687714
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.209604
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.379821
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.10968
        }
      }
    },
    {
      "caseId": "s41587-025-02654-4",
      "title": "Protein Tertiary Structure Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Structure Modeling",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": -0.456321,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.819704
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.464493
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.462575
        },
        "MiniMax-M2.7": {
          "state": "invalid",
          "value": null
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.462577
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.46199
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.461021
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.814767
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.456321
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.45997
        }
      }
    },
    {
      "caseId": "s41587-025-02688-8",
      "title": "Spatial RNA Velocity Inference",
      "domain": "Cellular Omics",
      "mlTaskType": "Simulation/Operator Learning",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": 1.614505,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.33862
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.386887
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.690023
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.599278
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.858771
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.296691
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.547955
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 1.469476
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 1.1835
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 1.614505
        }
      }
    },
    {
      "caseId": "s41592-022-01709-7",
      "title": "Cross-Modal Single-Cell Protein Data Matching",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "buggy",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": -0.082585,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.173738
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.160379
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.128355
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.596696
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.101602
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.150598
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.082585
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.118447
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.268804
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.13522
        }
      }
    },
    {
      "caseId": "s41592-023-01878-z",
      "title": "Macromolecular Particle Localization in Cryo-Electron Tomograms",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Segmentation/Detection",
      "taskDir": "part1",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": -0.425721,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.9875
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.996212
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.431818
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.9939
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.996212
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.996212
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.990115
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.425721
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.990115
        }
      }
    },
    {
      "caseId": "s41592-023-01940-w",
      "title": "Microbial Genome Quality Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Other Specialized",
      "taskDir": "buggy",
      "bestModel": "GPT-5.5",
      "bestScore": 0.002941,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.9339
        },
        "GPT-5.4": {
          "state": "invalid",
          "value": null
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.801472
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -1.1773
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -1.201675
        },
        "GLM-5.1": {
          "state": "none",
          "value": null
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.508224
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.380494
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.002941
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.933878
        }
      }
    },
    {
      "caseId": "s41592-023-01955-3",
      "title": "Contrastive Representation Learning for Single-Cell Treatment Response Analysis",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part1",
      "bestModel": "DeepSeek-V4-Pro",
      "bestScore": 2.375875,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 1.1571
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.387135
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 1.697217
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.5156
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 2.375875
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.042035
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.619838
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.538307
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 2.219814
        }
      }
    },
    {
      "caseId": "s41592-023-02032-5",
      "title": "De Novo Nucleic Acid Atomic Structure Modeling from Cryo-EM Maps",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Structure Modeling",
      "taskDir": "buggy",
      "bestModel": "GPT-5.5",
      "bestScore": 0.177989,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.072811
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.730425
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.813712
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -1
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.978436
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.955947
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.691689
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.731962
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.177989
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.134605
        }
      }
    },
    {
      "caseId": "s41592-023-02035-2",
      "title": "Single-Cell Cross-Study Label Transfer",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part1",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": 0.009413,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.0328
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.017975
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.007751
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.0087
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.023067
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.014801
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.000488
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.009413
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.005444
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.011141
        }
      }
    },
    {
      "caseId": "s41592-023-02124-2",
      "title": "Tissue Cellular Neighborhood Detection",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": 0.099578,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.071132
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.014476
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.026314
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.0016
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.067997
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.083189
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.076512
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.008763
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.017894
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.099578
        }
      }
    },
    {
      "caseId": "s41592-023-02148-8",
      "title": "RNA Family Sequence Generation",
      "domain": "Cellular Omics",
      "mlTaskType": "Generation/Design",
      "taskDir": "part1",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.264176,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.189081
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.406872
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -1
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -1
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -1
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.549066
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.264176
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.549066
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.233134
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.262516
        }
      }
    },
    {
      "caseId": "s41592-024-02191-z",
      "title": "Cross-Species Single-Cell RNA-seq Integration and Cell Type Label Transfer",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part2",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": 0.078535,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.549574
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.687761
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.003502
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.0253
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.4584
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.085947
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.221536
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.078535
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.034601
        }
      }
    },
    {
      "caseId": "s41592-024-02257-y",
      "title": "Spatial Domain Identification in Spatially Resolved Transcriptomics",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": 0.03534,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.324508
        },
        "GPT-5.4": {
          "state": "invalid",
          "value": null
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.381669
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.4952
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.3692
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.376952
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.199009
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.363515
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.03534
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.287963
        }
      }
    },
    {
      "caseId": "s41592-024-02316-4",
      "title": "Spatial Domain Identification from Multi-Omics Data",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part2",
      "bestModel": "GLM-5.1",
      "bestScore": 0.030928,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.029565
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.022865
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.030423
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.2801
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.021401
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.030928
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.030928
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.030928
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.030928
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.030928
        }
      }
    },
    {
      "caseId": "s41592-024-02372-w",
      "title": "Protein-DNA Binding Specificity Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": 0.567848,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -2.748048
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -1.210074
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -1
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -3.475
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -3.154807
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -2.062771
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -2.378192
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.567848
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.469891
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -1
        }
      }
    },
    {
      "caseId": "s41592-024-02523-z",
      "title": "Genomic Sequence Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": -0.066916,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.117533
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.147931
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.282205
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.12585
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.074808
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.150003
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.106704
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.124368
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.140866
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.066916
        }
      }
    },
    {
      "caseId": "s41592-024-02580-4",
      "title": "Microscopy Instance Segmentation",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Segmentation/Detection",
      "taskDir": "buggy",
      "bestModel": "GLM-5.1",
      "bestScore": 0.144277,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.104291
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.186276
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.525969
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.78044
        },
        "DeepSeek-V4-Pro": {
          "state": "none",
          "value": null
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.144277
        },
        "Gemini 3.5 Flash": {
          "state": "none",
          "value": null
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.709681
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.471217
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.779112
        }
      }
    },
    {
      "caseId": "s41592-025-02662-x",
      "title": "Fluorescence Microscopy Spot Detection",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Segmentation/Detection",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": -0.029985,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.084184
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.183913
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.173927
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.190688
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.188826
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.33859
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.086331
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.201276
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.085939
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.029985
        }
      }
    },
    {
      "caseId": "s41592-025-02665-8",
      "title": "Temporal Segmentation of Single-Particle Diffusion Trajectories",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.025132,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.077692
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.012719
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.017011
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.5064
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.080414
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.021312
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.025132
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.148848
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.014078
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.023149
        }
      }
    },
    {
      "caseId": "s41592-025-02776-2",
      "title": "Protein Variant Effect Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.125726,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.04418
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.11433
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.115033
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.08162
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.104599
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.102824
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.125726
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.120842
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.106339
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.120068
        }
      }
    },
    {
      "caseId": "s41592-025-02820-1",
      "title": "Restraint-Guided Protein Complex Structure Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Structure Modeling",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": -0.485823,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.887465
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.621869
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.884317
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.922443
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.936738
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.924956
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.888002
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.574215
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.485823
        }
      }
    },
    {
      "caseId": "s41592-025-02826-9",
      "title": "Cell Marker Positivity Classification in Multiplexed Imaging",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Classification",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": -0.10873,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.286011
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.144325
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.171474
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.371758
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.245389
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.205254
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.199009
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.233575
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.10873
        }
      }
    },
    {
      "caseId": "s41592-025-02854-5",
      "title": "Single-Cell Genomic Profile Prediction from DNA Sequence",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Opus 4.6",
      "bestScore": -0.2547,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.2547
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.749989
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.803464
        },
        "MiniMax-M2.7": {
          "state": "invalid",
          "value": null
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.870953
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.958737
        },
        "Gemini 3.5 Flash": {
          "state": "invalid",
          "value": null
        },
        "Qwen 3.7 Max": {
          "state": "invalid",
          "value": null
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.272825
        }
      }
    },
    {
      "caseId": "s41592-025-02870-5",
      "title": "Cell Differentiation Trajectory Inference",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": 0.053719,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.09074
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.063069
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.083883
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.080931
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.1195
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.055732
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.103466
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.025449
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.053719
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.002131
        }
      }
    },
    {
      "caseId": "s41592-025-02886-x",
      "title": "3D Cell Tracking in Time-Lapse Microscopy",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Segmentation/Detection",
      "taskDir": "part2",
      "bestModel": "Opus 4.6",
      "bestScore": -1,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -1
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -72.478248
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -206.034066
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -266.648469
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -42.341433
        },
        "GLM-5.1": {
          "state": "none",
          "value": null
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -32.194442
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -31.027349
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -131.507778
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -39.293409
        }
      }
    },
    {
      "caseId": "s41592-025-02893-y",
      "title": "Skeleton Keypoint Imputation",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Segmentation/Detection",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": -102.368049,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -137.89
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -215.281601
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -669.778501
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -562.5358
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -514.944511
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -436.824224
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -423.052183
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -178.088158
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -102.368049
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -357.455135
        }
      }
    },
    {
      "caseId": "s41592-025-02924-8",
      "title": "Clone Tree Site Labeling for Metastatic Migration History Inference",
      "domain": "Cellular Omics",
      "mlTaskType": "Other Specialized",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": -0.098553,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.218108
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.112903
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.16914
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.52116
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.319396
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.160862
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.323275
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.213936
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.098553
        }
      }
    },
    {
      "caseId": "s41592-025-02926-6",
      "title": "Spatial Omics Prediction from Histology and Cross-Modal Integration",
      "domain": "Cellular Omics",
      "mlTaskType": "Other Specialized",
      "taskDir": "part2",
      "bestModel": "Opus 4.6",
      "bestScore": 0.043211,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.043211
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.381441
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.706997
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.782242
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.4792
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.248735
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.174833
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.644829
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.266076
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.427785
        }
      }
    },
    {
      "caseId": "s41592-025-02983-x",
      "title": "Cell Behavior Prediction in Multicellular Embryogenesis",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "buggy",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.079227,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.136133
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.106194
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.142711
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.225123
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.563574
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.52082
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.079227
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.174429
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.08056
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.027163
        }
      }
    },
    {
      "caseId": "s42256-022-00447-x",
      "title": "Molecular Property Prediction",
      "domain": "Molecular Design",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": 0.113234,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.030092
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.030129
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.050284
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.530755
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.071633
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.137516
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.041137
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.382598
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.025261
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.113234
        }
      }
    },
    {
      "caseId": "s42256-022-00459-7",
      "title": "Peptide-HLA Class I Binding Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "Kimi K2.6",
      "bestScore": 0.015062,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.012373
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.01119
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.015062
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.007458
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.011337
        },
        "GLM-5.1": {
          "state": "none",
          "value": null
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.011686
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.01199
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.011772
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.013712
        }
      }
    },
    {
      "caseId": "s42256-022-00464-w",
      "title": "Multiscale Dynamical System Forecasting",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": 0.112349,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -2.841965
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.070701
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -6.254052
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -17.884319
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -2.966176
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -2.327706
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -41.012407
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -1.07958
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.112349
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.542854
        }
      }
    },
    {
      "caseId": "s42256-022-00468-6",
      "title": "Graph Combinatorial Optimization",
      "domain": "Relational Reasoning",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": 0.065105,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.0423
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.022316
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.05352
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.0863
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.051965
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.061642
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.060433
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.10373
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.063767
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.065105
        }
      }
    },
    {
      "caseId": "s42256-022-00501-8",
      "title": "Molecular Interactions and Properties Prediction",
      "domain": "Molecular Design",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": -0.06171,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.136263
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.123402
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.107036
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.377023
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.126583
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.155031
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.111639
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.105993
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.06171
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.134166
        }
      }
    },
    {
      "caseId": "s42256-022-00518-z",
      "title": "Single-Cell Atlas Mapping and Integration",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part1",
      "bestModel": "GPT-5.5",
      "bestScore": 0.223783,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.018084
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.075662
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.009367
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.244001
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.2605
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.051159
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.280843
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.057517
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.223783
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.008618
        }
      }
    },
    {
      "caseId": "s42256-022-00526-z",
      "title": "Organic Reaction Product Prediction",
      "domain": "Molecular Design",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": -0.293612,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.8929
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.529928
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.990143
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.9881
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.355396
        },
        "GLM-5.1": {
          "state": "none",
          "value": null
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.416602
        },
        "Qwen 3.7 Max": {
          "state": "none",
          "value": null
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.293612
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.395072
        }
      }
    },
    {
      "caseId": "s42256-022-00534-z",
      "title": "Single-Cell RNA-seq Cell Type Annotation",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part1",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.010101,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.05924
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.00054
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.001352
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.181019
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.300293
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.035809
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.010101
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.00458
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.003172
        }
      }
    },
    {
      "caseId": "s42256-022-00541-0",
      "title": "Clinical Drug Response Prediction from Cell-Line Screens",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": -0.100466,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.236741
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.233545
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.214875
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.250079
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.326943
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.213348
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.201722
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.244965
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.107651
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.100466
        }
      }
    },
    {
      "caseId": "s42256-022-00556-7",
      "title": "Temporal Sequence Modeling with Irregular Sampling",
      "domain": "Relational Reasoning",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "Opus 4.6",
      "bestScore": -0.6011,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.6011
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.733515
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.69723
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.7864
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.781817
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.618639
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.610949
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.773922
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.619018
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.691329
        }
      }
    },
    {
      "caseId": "s42256-023-00611-x",
      "title": "Categorical Counterfactual Outcome Estimation",
      "domain": "Relational Reasoning",
      "mlTaskType": "Classification",
      "taskDir": "part1",
      "bestModel": "GPT-5.5",
      "bestScore": 0.025213,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.016832
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.02267
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.021621
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.010705
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.023362
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.019692
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.020899
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.019214
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.025213
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.023583
        }
      }
    },
    {
      "caseId": "s42256-023-00619-3",
      "title": "TCR-Peptide Binding Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Classification",
      "taskDir": "part1",
      "bestModel": "Opus 4.7",
      "bestScore": 0.186987,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.1297
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.046515
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.118304
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.1513
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.03842
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.115788
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.065068
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.162721
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.186987
        }
      }
    },
    {
      "caseId": "s42256-023-00627-3",
      "title": "Metabolomic Profile Prediction from Microbial Composition",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "buggy",
      "bestModel": "GPT-5.5",
      "bestScore": 0.54351,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.102007
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.038007
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.028237
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.251138
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.003704
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.077531
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.107369
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.017332
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.54351
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.461563
        }
      }
    },
    {
      "caseId": "s42256-023-00628-2",
      "title": "Metal-Organic Framework Property Prediction",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part1",
      "bestModel": "DeepSeek-V4-Pro",
      "bestScore": 0.008591,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.0595
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.066818
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.035927
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.0952
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.008591
        },
        "GLM-5.1": {
          "state": "none",
          "value": null
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.038016
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.073962
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.053165
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.058089
        }
      }
    },
    {
      "caseId": "s42256-023-00630-8",
      "title": "Visual Abstract Reasoning on Progressive Matrices",
      "domain": "Relational Reasoning",
      "mlTaskType": "Classification",
      "taskDir": "buggy",
      "bestModel": "GPT-5.5",
      "bestScore": -0.312354,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.794603
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.750717
        },
        "Kimi K2.6": {
          "state": "none",
          "value": null
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.858325
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.654805
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.496481
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.715454
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.586018
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.312354
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.514235
        }
      }
    },
    {
      "caseId": "s42256-023-00636-2",
      "title": "Targeted Molecular Generation via SMILES-Based Optimization",
      "domain": "Molecular Design",
      "mlTaskType": "Generation/Design",
      "taskDir": "part1",
      "bestModel": "Opus 4.6",
      "bestScore": 0.0205,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.0205
        },
        "GPT-5.4": {
          "state": "invalid",
          "value": null
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.321796
        },
        "MiniMax-M2.7": {
          "state": "invalid",
          "value": null
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.321796
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.320424
        },
        "Gemini 3.5 Flash": {
          "state": "invalid",
          "value": null
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.321796
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.020453
        }
      }
    },
    {
      "caseId": "s42256-023-00639-z",
      "title": "Molecular and Protein Property Prediction",
      "domain": "Molecular Design",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": 0.098143,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.062189
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.043921
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.062547
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.424192
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.046981
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.043395
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.072079
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.057948
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.062053
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.098143
        }
      }
    },
    {
      "caseId": "s42256-023-00640-6",
      "title": "Drug Interaction Prediction on Biomedical Networks",
      "domain": "Molecular Design",
      "mlTaskType": "Classification",
      "taskDir": "part2",
      "bestModel": "DeepSeek-V4-Pro",
      "bestScore": 0.056342,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.012269
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.006231
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.01799
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.047752
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.056342
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.031216
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.007022
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.053481
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.01871
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.023661
        }
      }
    },
    {
      "caseId": "s42256-023-00654-0",
      "title": "Molecular Property Prediction",
      "domain": "Molecular Design",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": -0.134862,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.306882
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.286586
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.261661
        },
        "MiniMax-M2.7": {
          "state": "none",
          "value": null
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.300408
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.289457
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.267457
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.314436
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.187489
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.134862
        }
      }
    },
    {
      "caseId": "s42256-023-00712-7",
      "title": "Pocket-Conditioned 3D Molecular Generation",
      "domain": "Molecular Design",
      "mlTaskType": "Generation/Design",
      "taskDir": "part2",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": -0.085886,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.154954
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.145101
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.141917
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.1668
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.1727
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.123576
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.140901
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.085886
        },
        "GPT-5.5": {
          "state": "none",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.09337
        }
      }
    },
    {
      "caseId": "s42256-024-00790-1",
      "title": "X-ray Diffraction Data Denoising",
      "domain": "Physical Modeling",
      "mlTaskType": "Simulation/Operator Learning",
      "taskDir": "part2",
      "bestModel": "Opus 4.6",
      "bestScore": 0.022751,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.022751
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.063828
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.086504
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -1
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.075182
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.075069
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.098317
        },
        "Qwen 3.7 Max": {
          "state": "invalid",
          "value": null
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.055302
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.020872
        }
      }
    },
    {
      "caseId": "s42256-024-00795-w",
      "title": "Protein Function Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": 0.000473,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.1787
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.027201
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.062554
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.041
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.1091
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.171909
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.002306
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.061468
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.000473
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.030017
        }
      }
    },
    {
      "caseId": "s42256-024-00815-9",
      "title": "Molecular Linker Design",
      "domain": "Molecular Design",
      "mlTaskType": "Generation/Design",
      "taskDir": "buggy",
      "bestModel": "Opus 4.6",
      "bestScore": 0.066559,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.066559
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.573058
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.91589
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.430793
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.5927
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.369378
        },
        "Gemini 3.5 Flash": {
          "state": "invalid",
          "value": null
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.494473
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.573058
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.487645
        }
      }
    },
    {
      "caseId": "s42256-024-00833-7",
      "title": "Graph and Hypergraph MaxCut Optimization",
      "domain": "Relational Reasoning",
      "mlTaskType": "Classification",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": 0.012775,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.012496
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.011239
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.012147
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.008447
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.011798
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.008552
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.012287
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.009355
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.012636
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.012775
        }
      }
    },
    {
      "caseId": "s42256-024-00836-4",
      "title": "RNA Sequence Analysis",
      "domain": "Cellular Omics",
      "mlTaskType": "Other Specialized",
      "taskDir": "part1",
      "bestModel": "GPT-5.5",
      "bestScore": -0.029065,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.1193
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.06792
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.037066
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.272898
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.547832
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.263053
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.131625
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.243975
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.029065
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.088976
        }
      }
    },
    {
      "caseId": "s42256-024-00838-2",
      "title": "Protein Sequence Design (Inverse Protein Folding)",
      "domain": "Protein Biology",
      "mlTaskType": "Generation/Design",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": -0.026325,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.052719
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.077816
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.076884
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.883711
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.07033
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.077912
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.073981
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.132929
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.128314
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.026325
        }
      }
    },
    {
      "caseId": "s42256-024-00892-w",
      "title": "Neuron Segmentation and Activity Trace Extraction from Calcium Imaging Data",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Kimi K2.6",
      "bestScore": 0.002676,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.407409
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.123316
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.002676
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.561656
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.4328
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.180904
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.083132
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.064336
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.141715
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.016278
        }
      }
    },
    {
      "caseId": "s42256-024-00916-5",
      "title": "Multiproperty Molecular Optimization",
      "domain": "Molecular Design",
      "mlTaskType": "Generation/Design",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": 0.200449,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.64794
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.67221
        },
        "Kimi K2.6": {
          "state": "none",
          "value": null
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.670412
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.537378
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.546816
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.64794
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.402697
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.316554
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.200449
        }
      }
    },
    {
      "caseId": "s42256-024-00956-x",
      "title": "Molecular Energy and Force Prediction",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": 0.232758,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -1.578366
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -1.338
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -3.512517
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -1
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -13.874583
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -1.984826
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.440036
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.232758
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.938338
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.304153
        }
      }
    },
    {
      "caseId": "s42256-025-01002-0",
      "title": "Peptide-MHC-TCR Binding Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Classification",
      "taskDir": "part1",
      "bestModel": "GPT-5.5",
      "bestScore": 0.030674,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.026912
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.015884
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.01074
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.015036
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.00286
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.018809
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.004583
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.013951
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.030674
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.019965
        }
      }
    },
    {
      "caseId": "s42256-025-01003-z",
      "title": "DNA Sequence Reconstruction from Noisy Reads",
      "domain": "Cellular Omics",
      "mlTaskType": "Generation/Design",
      "taskDir": "part1",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": -0.011213,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.0545
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -1.411494
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.841381
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -1
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -5.99129
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.66429
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.011213
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.377849
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.058201
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.356022
        }
      }
    },
    {
      "caseId": "s42256-025-01010-0",
      "title": "Transition State Structure Generation",
      "domain": "Molecular Design",
      "mlTaskType": "Generation/Design",
      "taskDir": "part1",
      "bestModel": "DeepSeek-V4-Pro",
      "bestScore": -1.265223,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -1.40272
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -1.443432
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -2.321255
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -3.424499
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -1.265223
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -2.208068
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -1.45134
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -2.020958
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -1.384002
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -1.352497
        }
      }
    },
    {
      "caseId": "s42256-025-01016-8",
      "title": "Disease-Specific Variant Effect Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "GLM-5.1",
      "bestScore": 0.325133,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.139099
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.098365
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.057598
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.208178
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.211367
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.325133
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.247055
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.313877
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.018968
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.075946
        }
      }
    },
    {
      "caseId": "s42256-025-01019-5",
      "title": "De Novo Peptide Sequencing from Tandem Mass Spectrometry",
      "domain": "Protein Biology",
      "mlTaskType": "Structure Modeling",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": 0.078994,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.037064
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.168425
        },
        "Kimi K2.6": {
          "state": "invalid",
          "value": null
        },
        "MiniMax-M2.7": {
          "state": "invalid",
          "value": null
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -1
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -1
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.058663
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.86813
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.078994
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.178451
        }
      }
    },
    {
      "caseId": "s42256-025-01026-6",
      "title": "Enzyme Optimum pH Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": 0.08966,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.036371
        },
        "GPT-5.4": {
          "state": "invalid",
          "value": null
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.010791
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.167759
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.028062
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.019418
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.00223
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.041068
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.038889
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.08966
        }
      }
    },
    {
      "caseId": "s42256-025-01042-6",
      "title": "Inverse Protein Folding",
      "domain": "Protein Biology",
      "mlTaskType": "Generation/Design",
      "taskDir": "part2",
      "bestModel": "Qwen 3.7 Max",
      "bestScore": -0.177836,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.382301
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.590069
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.602853
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.597003
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.495192
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.549518
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.304823
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.177836
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.46682
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.192747
        }
      }
    },
    {
      "caseId": "s43588-024-00689-2",
      "title": "Multimodal Single-Cell RNA-seq Cell Type Clustering",
      "domain": "Cellular Omics",
      "mlTaskType": "Clustering/Integration",
      "taskDir": "part1",
      "bestModel": "Opus 4.7",
      "bestScore": 0.218032,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.129587
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.120274
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.133056
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.0124
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.0805
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.130972
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.139012
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.123182
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.207512
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.218032
        }
      }
    },
    {
      "caseId": "s43588-024-00698-1",
      "title": "Genetic Perturbation Outcome Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part1",
      "bestModel": "Opus 4.7",
      "bestScore": 0.006001,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.003924
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.001634
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.003846
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.084978
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.000328
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.003038
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.001388
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.00464
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.001031
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.006001
        }
      }
    },
    {
      "caseId": "s43588-024-00703-7",
      "title": "Anomalous Diffusion Out-of-Distribution Dynamics Detection",
      "domain": "Physical Modeling",
      "mlTaskType": "Classification",
      "taskDir": "part1",
      "bestModel": "GLM-5.1",
      "bestScore": 0.534016,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.111591
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.477928
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.348471
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.0533
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.086407
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.534016
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.380737
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.167689
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.531048
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.468486
        }
      }
    },
    {
      "caseId": "s43588-024-00716-2",
      "title": "Protein Stability Change Prediction Upon Mutations",
      "domain": "Protein Biology",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "buggy",
      "bestModel": "Opus 4.7",
      "bestScore": 0.09551,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.159009
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.502628
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.169482
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.322506
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.283615
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.149889
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.496901
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.229975
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.405549
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.09551
        }
      }
    },
    {
      "caseId": "s43588-024-00730-4",
      "title": "Electronic Structure Energy Computation",
      "domain": "Physical Modeling",
      "mlTaskType": "Simulation/Operator Learning",
      "taskDir": "part1",
      "bestModel": "Opus 4.7",
      "bestScore": -7.346038,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -24.9062
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -21.281593
        },
        "Kimi K2.6": {
          "state": "none",
          "value": null
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -167.824249
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -161.549994
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -293.358605
        },
        "Gemini 3.5 Flash": {
          "state": "invalid",
          "value": null
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -33.692729
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -7.346038
        }
      }
    },
    {
      "caseId": "s43588-024-00732-2",
      "title": "Geometry-Dependent PDE Solution Operator Learning",
      "domain": "Physical Modeling",
      "mlTaskType": "Simulation/Operator Learning",
      "taskDir": "part1",
      "bestModel": "Opus 4.7",
      "bestScore": 0.22894,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.11812
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -2.081029
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -1.177649
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.541159
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -3.033159
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.451841
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.424727
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -1.219005
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.048074
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.22894
        }
      }
    },
    {
      "caseId": "s43588-024-00733-1",
      "title": "Protein Essentiality Prediction",
      "domain": "Protein Biology",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part1",
      "bestModel": "Opus 4.6",
      "bestScore": 0.018837,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.018837
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.007622
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.008147
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.052334
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.001522
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.002007
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.012013
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.014137
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.01023
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.018201
        }
      }
    },
    {
      "caseId": "s43588-024-00757-7",
      "title": "Electronic Circular Dichroism Spectrum Peak Property Prediction",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "buggy",
      "bestModel": "Kimi K2.6",
      "bestScore": 0.350783,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.245136
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.350076
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.350783
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.395805
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.266839
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.076041
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.250084
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.136813
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.2043
        }
      }
    },
    {
      "caseId": "s43588-024-00765-7",
      "title": "Single-Cell Phenotype Prediction",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": 0.094202,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.0868
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.132114
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": 0.090336
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.0008
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.088833
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.093698
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.087604
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.989063
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.094202
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.078265
        }
      }
    },
    {
      "caseId": "s43588-025-00798-6",
      "title": "COVID-19 Hospitalization Trend Forecasting",
      "domain": "Biomedical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.719264,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.012487
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.105987
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.018656
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.521043
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.070178
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.487625
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.719264
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.006104
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.005221
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.017463
        }
      }
    },
    {
      "caseId": "s43588-025-00842-5",
      "title": "Zeolite-Molecule Binding Affinity Prediction",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Gemini 3.5 Flash",
      "bestScore": 0.278988,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.008591
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.183725
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.064631
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.105134
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.157477
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.000355
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.278988
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.039845
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.031297
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.274184
        }
      }
    },
    {
      "caseId": "s43588-025-00872-z",
      "title": "Ground-State Energy Prediction for Periodic Solids",
      "domain": "Physical Modeling",
      "mlTaskType": "Simulation/Operator Learning",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": 0.561534,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.249273
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.175345
        },
        "Kimi K2.6": {
          "state": "none",
          "value": null
        },
        "MiniMax-M2.7": {
          "state": "invalid",
          "value": null
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.017324
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.012931
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.104133
        },
        "Qwen 3.7 Max": {
          "state": "invalid",
          "value": null
        },
        "GPT-5.5": {
          "state": "invalid",
          "value": null
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.561534
        }
      }
    },
    {
      "caseId": "s43588-025-00878-7",
      "title": "Noncoding Variant Effect Prediction on Gene Expression",
      "domain": "Cellular Omics",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "buggy",
      "bestModel": "GPT-5.5",
      "bestScore": 0.164982,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.121066
        },
        "GPT-5.4": {
          "state": "valid",
          "value": 0.015417
        },
        "Kimi K2.6": {
          "state": "none",
          "value": null
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": 0.122564
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": 0.1457
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.123885
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": 0.116984
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.089234
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.164982
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.158529
        }
      }
    },
    {
      "caseId": "s43588-025-00903-9",
      "title": "Polymer Property Prediction",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Opus 4.7",
      "bestScore": 0.040272,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.3813
        },
        "GPT-5.4": {
          "state": "invalid",
          "value": null
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -0.365203
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.745639
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.400182
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.484214
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.381769
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -0.540005
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.408044
        },
        "Opus 4.7": {
          "state": "valid",
          "value": 0.040272
        }
      }
    },
    {
      "caseId": "s43588-025-00917-3",
      "title": "Upconverting Nanoparticle Emission Intensity Prediction",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "Opus 4.6",
      "bestScore": 0.326315,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": 0.326315
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -1.328045
        },
        "Kimi K2.6": {
          "state": "valid",
          "value": -1.450749
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -2.234955
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -3.164249
        },
        "GLM-5.1": {
          "state": "valid",
          "value": -0.837865
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -1.140552
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": -1.750234
        },
        "GPT-5.5": {
          "state": "valid",
          "value": -0.904628
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.489631
        }
      }
    },
    {
      "caseId": "s43588-025-00920-8",
      "title": "Stereoselectivity Prediction in Asymmetric Catalytic Reactions",
      "domain": "Physical Modeling",
      "mlTaskType": "Prediction/Regression",
      "taskDir": "part2",
      "bestModel": "GPT-5.5",
      "bestScore": 0.171103,
      "scores": {
        "Opus 4.6": {
          "state": "valid",
          "value": -0.0321
        },
        "GPT-5.4": {
          "state": "valid",
          "value": -0.546132
        },
        "Kimi K2.6": {
          "state": "invalid",
          "value": null
        },
        "MiniMax-M2.7": {
          "state": "valid",
          "value": -0.7369
        },
        "DeepSeek-V4-Pro": {
          "state": "valid",
          "value": -0.603325
        },
        "GLM-5.1": {
          "state": "valid",
          "value": 0.097959
        },
        "Gemini 3.5 Flash": {
          "state": "valid",
          "value": -0.023611
        },
        "Qwen 3.7 Max": {
          "state": "valid",
          "value": 0.006448
        },
        "GPT-5.5": {
          "state": "valid",
          "value": 0.171103
        },
        "Opus 4.7": {
          "state": "valid",
          "value": -0.050454
        }
      }
    }
  ],
  "taxonomy": {
    "domains": [
      {
        "label": "Cellular Omics"
      },
      {
        "label": "Protein Biology"
      },
      {
        "label": "Biomedical Modeling"
      },
      {
        "label": "Physical Modeling"
      },
      {
        "label": "Molecular Design"
      },
      {
        "label": "Relational Reasoning"
      }
    ],
    "taskTypes": [
      {
        "label": "Prediction/Regression"
      },
      {
        "label": "Classification"
      },
      {
        "label": "Clustering/Integration"
      },
      {
        "label": "Generation/Design"
      },
      {
        "label": "Segmentation/Detection"
      },
      {
        "label": "Simulation/Operator Learning"
      },
      {
        "label": "Structure Modeling"
      },
      {
        "label": "Other Specialized"
      }
    ]
  }
};
