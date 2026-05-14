# Audit task

You are auditing a shard of moneo-sense-sweep records for translation, grammar,
naturalness, and consistency problems. Your job is to FLAG only entries
with clear, defensible defects, with direct-source evidence for each flag.

## Verdict taxonomy

Use exactly one of: pos_mismatch, wrong_sense, target_form_drift, mistranslation

## Evidence policy

- Every flag MUST carry an `evidence` object: `{type, value, note?}`.
- Allowed types: url, corpus-rule, in-game-canon
- For `type: "url"` value MUST be an http(s) URL to a direct source.
- DO NOT cite AI Overview snippets, AI answer summaries, or generated
  blog content. Naver Korean Dictionary, Standard Korean Dictionary,
  official Pokemon Korea pages, and similar primary sources are OK.
- For `type: "corpus-rule"` value is the rule (e.g. "noun-noun compound,
  no internal space"); use only when an authoritative URL isn't a fit.
- For `type: "in-game-canon"` value is the ROM-anchored fact (e.g.
  "Struggle fires automatically when PP is exhausted").
- Disallowed hosts: google.com/search, google.com/aio, bing.com/search?q=

If you can't produce evidence, DO NOT FLAG — leave the entry alone.

## Output

Emit exactly one JSON object, no prose, matching:

```
{
  "shardFile": "app/src/main/assets/moneo/sentences-ko-themed-mined.json",
  "range": [400, 586],
  "inspected": 186,
  "flagged": [
    {
      "key": "<value of the vocabId field>",
      "verdict": "<one of: pos_mismatch, wrong_sense, target_form_drift, mistranslation>",
      "issue": "<concise prose>",
      "suggestion": "<replacement text or 'regloss to ...'>",
      "evidence": {"type": "url|corpus-rule|in-game-canon", "value": "...", "note": null},
      "originalValue": {"<auditField>": "<snapshot>"},
      "proposedValue": {"<dataset field to set>": "<new value>"}
    }
  ],
  "auditor": "llm-claude-opus-4-7",
  "auditedAt": "<ISO date>"
}
```

`originalValue` should snapshot the audited fields so the reviewer UI can
diff. `proposedValue` is what the applier will write into the entry if the
reviewer accepts; if you only want to suggest in prose, omit it and put
the suggestion in `suggestion`.

## Shard

Below is the list of 186 entries. For each, decide: leave alone OR
flag with evidence. Be conservative — only flag clear, defensible defects.

```
[
  {
    "vocabId": "rom-mine-v3:미래예지",
    "korean": "포켓몬이 미래예지를 배웠어요.",
    "gloss": "The Pokémon learned Future Sight.",
    "targetForm": "미래예지",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "cerulean_cave",
      "pewter_city",
      "route_11",
      "route_24"
    ]
  },
  {
    "vocabId": "rom-mine-v3:바위깨기",
    "korean": "트레이너가 포켓몬에게 바위깨기를 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Rock Smash.",
    "targetForm": "바위깨기",
    "areaId": "fuchsia_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "fuchsia_city",
    "areasReferenced": [
      "fuchsia_city"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:바다회오리",
    "korean": "친구의 포켓몬이 바다회오리를 잘 써요.",
    "gloss": "My friend's Pokémon uses Whirlpool well.",
    "targetForm": "바다회오리",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:집단구타",
    "korean": "집단구타는 포켓몬이 시합에서 쓰는 기술이에요.",
    "gloss": "Beat Up is a move Pokémon use in battle.",
    "targetForm": "집단구타",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:소란피기",
    "korean": "체육관 시합에서 소란피기를 사용했어요.",
    "gloss": "I used Uproar in the gym match.",
    "targetForm": "소란피기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_16",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_16"
    ]
  },
  {
    "vocabId": "rom-mine-v3:비축하기",
    "korean": "기술 목록에 비축하기가 있어요.",
    "gloss": "Stockpile is on the move list.",
    "targetForm": "비축하기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "pewter_city",
      "route_12"
    ]
  },
  {
    "vocabId": "rom-mine-v3:토해내기",
    "korean": "포켓몬이 시합에서 토해내기를 보여 줬어요.",
    "gloss": "The Pokémon showed off Spit Up in the match.",
    "targetForm": "토해내기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "pewter_city",
      "route_12"
    ]
  },
  {
    "vocabId": "rom-mine-v3:꿀꺽",
    "korean": "꿀꺽은 트레이너의 자랑이에요.",
    "gloss": "Swallow is the trainer's pride.",
    "targetForm": "꿀꺽",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "areasReferenced": [
      "rom_mined",
      "pewter_city",
      "route_12"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text",
      "pokemon_species"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      4777
    ]
  },
  {
    "vocabId": "rom-mine-v3:열풍",
    "korean": "친구가 열풍을 처음 봤어요.",
    "gloss": "My friend saw Heat Wave for the first time.",
    "targetForm": "열풍",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined",
      "pallet_town",
      "route_23"
    ],
    "liveRecIds": [
      7266
    ]
  },
  {
    "vocabId": "rom-mine-v3:싸라기눈",
    "korean": "이 포켓몬은 싸라기눈을 익히는 중이에요.",
    "gloss": "This Pokémon is learning Hail.",
    "targetForm": "싸라기눈",
    "areaId": "seafoam_islands",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "seafoam_islands",
    "areasReferenced": [
      "seafoam_islands",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      4593
    ]
  },
  {
    "vocabId": "rom-mine-v3:트집",
    "korean": "포켓몬이 '트집'을 써서 상대가 같은 기술을 연속으로 쓰지 못했어요.",
    "gloss": "The Pokémon used Torment so the opponent could not use the same move repeatedly.",
    "targetForm": "트집",
    "areaId": "lavender_town",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "lavender_town",
    "areasReferenced": [
      "lavender_town",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      4689
    ]
  },
  {
    "vocabId": "rom-mine-v3:부추기기",
    "korean": "선배가 부추기기의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Flatter.",
    "targetForm": "부추기기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_3",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_3"
    ]
  },
  {
    "vocabId": "rom-mine-v3:도깨비불",
    "korean": "포켓몬이 도깨비불을 배웠어요.",
    "gloss": "The Pokémon learned Will-O-Wisp.",
    "targetForm": "도깨비불",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7270
    ]
  },
  {
    "vocabId": "rom-mine-v3:추억의선물",
    "korean": "트레이너가 포켓몬에게 추억의선물을 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Memento.",
    "targetForm": "추억의선물",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "celadon_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "celadon_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:객기",
    "korean": "친구의 포켓몬이 객기를 잘 써요.",
    "gloss": "My friend's Pokémon uses Facade well.",
    "targetForm": "객기",
    "areaId": "lavender_town",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "lavender_town",
    "areasReferenced": [
      "lavender_town",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      7272
    ]
  },
  {
    "vocabId": "rom-mine-v3:힘껏펀치",
    "korean": "힘껏펀치는 포켓몬이 시합에서 쓰는 기술이에요.",
    "gloss": "Focus Punch is a move Pokémon use in battle.",
    "targetForm": "힘껏펀치",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:정신차리기",
    "korean": "체육관 시합에서 정신차리기를 사용했어요.",
    "gloss": "I used Smelling Salts in the gym match.",
    "targetForm": "정신차리기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:날따름",
    "korean": "기술 목록에 날따름이 있어요.",
    "gloss": "Follow Me is on the move list.",
    "targetForm": "날따름",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_6",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_6"
    ]
  },
  {
    "vocabId": "rom-mine-v3:자연의힘",
    "korean": "포켓몬이 시합에서 자연의힘을 보여 줬어요.",
    "gloss": "The Pokémon showed off Nature Power in the match.",
    "targetForm": "자연의힘",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:충전",
    "korean": "충전은 트레이너의 자랑이에요.",
    "gloss": "Charge is the trainer's pride.",
    "targetForm": "충전",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "viridian_city",
    "areasReferenced": [
      "viridian_city",
      "route_2",
      "pewter_city",
      "route_4",
      "cerulean_city",
      "saffron_city",
      "lavender_town",
      "route_10",
      "route_11",
      "vermilion_city",
      "fuchsia_city",
      "route_18",
      "cinnabar_island",
      "celadon_city",
      "indigo_plateau",
      "rom_mined",
      "six_island",
      "two_island",
      "seven_island",
      "three_island",
      "one_island",
      "five_island",
      "four_island"
    ],
    "sourceTypes": [
      "npc_dialog",
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      2325
    ]
  },
  {
    "vocabId": "rom-mine-v3:도발",
    "korean": "친구가 도발을 처음 봤어요.",
    "gloss": "My friend saw Taunt for the first time.",
    "targetForm": "도발",
    "areaId": "lavender_town",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "lavender_town",
    "areasReferenced": [
      "lavender_town",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      4654
    ]
  },
  {
    "vocabId": "rom-mine-v3:도우미",
    "korean": "이 포켓몬은 도우미를 익히는 중이에요.",
    "gloss": "This Pokémon is learning Helping Hand.",
    "targetForm": "도우미",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_3",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_13",
      "route_23",
      "route_3"
    ]
  },
  {
    "vocabId": "rom-mine-v3:트릭",
    "korean": "포켓몬이 '트릭'으로 상대와 지닌 도구를 바꿨어요.",
    "gloss": "The Pokémon used Trick to swap held items with the opponent.",
    "targetForm": "트릭",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "lavender_town",
    "areasReferenced": [
      "lavender_town",
      "vermilion_city",
      "rom_mined"
    ],
    "sourceTypes": [
      "npc_dialog",
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      2350
    ]
  },
  {
    "vocabId": "rom-mine-v3:역할",
    "korean": "선배가 역할의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Role Play.",
    "targetForm": "역할",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_24",
    "areasReferenced": [
      "rom_mined",
      "route_24"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      6505
    ]
  },
  {
    "vocabId": "rom-mine-v3:희망사항",
    "korean": "포켓몬이 희망사항을 배웠어요.",
    "gloss": "The Pokémon learned Wish.",
    "targetForm": "희망사항",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:조수",
    "korean": "트레이너가 포켓몬에게 조수를 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Assist.",
    "targetForm": "조수",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "areasReferenced": [
      "pallet_town",
      "route_2",
      "route_4",
      "route_5",
      "route_6",
      "saffron_city",
      "route_7",
      "route_8",
      "route_10",
      "rom_mined"
    ],
    "sourceTypes": [
      "npc_dialog",
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      2079,
      2859
    ]
  },
  {
    "vocabId": "rom-mine-v3:뿌리박기",
    "korean": "친구의 포켓몬이 뿌리박기를 잘 써요.",
    "gloss": "My friend's Pokémon uses Ingrain well.",
    "targetForm": "뿌리박기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:엄청난힘",
    "korean": "엄청난힘은 포켓몬이 시합에서 쓰는 기술이에요.",
    "gloss": "Superpower is a move Pokémon use in battle.",
    "targetForm": "엄청난힘",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:매직코트",
    "korean": "체육관 시합에서 매직코트를 사용했어요.",
    "gloss": "I used Magic Coat in the gym match.",
    "targetForm": "매직코트",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:리사이클",
    "korean": "기술 목록에 리사이클이 있어요.",
    "gloss": "Recycle is on the move list.",
    "targetForm": "리사이클",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "celadon_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "celadon_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:리벤지",
    "korean": "포켓몬이 시합에서 리벤지를 보여 줬어요.",
    "gloss": "The Pokémon showed off Revenge in the match.",
    "targetForm": "리벤지",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "cerulean_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined",
      "cerulean_city",
      "saffron_city"
    ],
    "liveRecIds": [
      7288
    ]
  },
  {
    "vocabId": "rom-mine-v3:깨트리다",
    "korean": "'깨트리다'라는 기술은 트레이너의 자랑이에요.",
    "gloss": "Brick Break is the trainer's pride.",
    "targetForm": "깨트리다",
    "areaId": "celadon_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "auditFix": {
      "verdict": "polish:fix",
      "issue": "Confirmed: attaching the topic particle 는 directly to the dictionary form 깨트리다 produces a parse collision with the quotative reduction -ㄴ다는 / -다는. Korean readers will hear 깨트리다는 as a malformed quotative rather than 'the move 깨트리다'. The fix uses the (이)라는 naming particle which is the standard way to cite a name/term in Korean.",
      "evidenceUrl": "https://123learnkorean.wordpress.com/2009/08/25/%EC%9D%B4%EB%9D%BC%EB%8A%94-called/",
      "auditedAt": "2026-05-09"
    },
    "firstAreaEncountered": "celadon_city",
    "areasReferenced": [
      "celadon_city",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      7289
    ]
  },
  {
    "vocabId": "rom-mine-v3:하품",
    "korean": "친구가 하품을 처음 봤어요.",
    "gloss": "My friend saw Yawn for the first time.",
    "targetForm": "하품",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "areasReferenced": [
      "rom_mined",
      "cinnabar_island",
      "pallet_town",
      "route_12"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      6515
    ]
  },
  {
    "vocabId": "rom-mine-v3:탁쳐서떨구기",
    "korean": "이 포켓몬은 탁쳐서떨구기를 익히는 중이에요.",
    "gloss": "This Pokémon is learning Knock Off.",
    "targetForm": "탁쳐서떨구기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:죽기살기",
    "korean": "포켓몬이 죽기살기를 사용했어요.",
    "gloss": "The Pokémon used Endeavor.",
    "targetForm": "죽기살기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_1",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_1",
      "route_2",
      "route_24"
    ]
  },
  {
    "vocabId": "rom-mine-v3:분화",
    "korean": "선배가 분화의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Eruption.",
    "targetForm": "분화",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      791
    ]
  },
  {
    "vocabId": "rom-mine-v3:스킬스웹",
    "korean": "포켓몬이 스킬스웹을 배웠어요.",
    "gloss": "The Pokémon learned Skill Swap.",
    "targetForm": "스킬스웹",
    "areaId": "celadon_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "celadon_city",
    "areasReferenced": [
      "celadon_city"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:봉인",
    "korean": "트레이너가 포켓몬에게 봉인을 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Imprison.",
    "targetForm": "봉인",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      4620
    ]
  },
  {
    "vocabId": "rom-mine-v3:리프레쉬",
    "korean": "친구의 포켓몬이 리프레쉬를 잘 써요.",
    "gloss": "My friend's Pokémon uses Refresh well.",
    "targetForm": "리프레쉬",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:원념",
    "korean": "원념은 상대 기술의 기술포인트를 없애는 기술이에요.",
    "gloss": "Grudge is a move that removes the opponent's move points.",
    "targetForm": "원념",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      4670
    ]
  },
  {
    "vocabId": "rom-mine-v3:가로챔",
    "korean": "체육관 시합에서 가로챔을 사용했어요.",
    "gloss": "I used Snatch in the gym match.",
    "targetForm": "가로챔",
    "areaId": "rocket_hideout",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rocket_hideout",
    "areasReferenced": [
      "rocket_hideout"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:비밀의힘",
    "korean": "기술 목록에 비밀의힘이 있어요.",
    "gloss": "Secret Power is on the move list.",
    "targetForm": "비밀의힘",
    "areaId": "saffron_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "saffron_city",
    "areasReferenced": [
      "saffron_city"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:다이빙",
    "korean": "포켓몬이 시합에서 다이빙을 보여 줬어요.",
    "gloss": "The Pokémon showed off Dive in the match.",
    "targetForm": "다이빙",
    "areaId": "seafoam_islands",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "seafoam_islands",
    "areasReferenced": [
      "seafoam_islands",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      3941
    ]
  },
  {
    "vocabId": "rom-mine-v3:손바닥치기",
    "korean": "손바닥치기는 트레이너의 자랑이에요.",
    "gloss": "Arm Thrust is the trainer's pride.",
    "targetForm": "손바닥치기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:보호색",
    "korean": "친구가 보호색을 처음 봤어요.",
    "gloss": "My friend saw Camouflage for the first time.",
    "targetForm": "보호색",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "fuchsia_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined",
      "fuchsia_city"
    ],
    "liveRecIds": [
      7302
    ]
  },
  {
    "vocabId": "rom-mine-v3:반딧불",
    "korean": "이 포켓몬은 반딧불을 익히는 중이에요.",
    "gloss": "This Pokémon is learning Tail Glow.",
    "targetForm": "반딧불",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7303
    ]
  },
  {
    "vocabId": "rom-mine-v3:라스트버지",
    "korean": "포켓몬이 라스트버지를 사용했어요.",
    "gloss": "The Pokémon used Luster Purge.",
    "targetForm": "라스트버지",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:미스트볼",
    "korean": "선배가 미스트볼의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Mist Ball.",
    "targetForm": "미스트볼",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:깃털댄스",
    "korean": "포켓몬이 깃털댄스를 배웠어요.",
    "gloss": "The Pokémon learned Feather Dance.",
    "targetForm": "깃털댄스",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_1",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_1",
      "route_13",
      "saffron_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:흔들흔들댄스",
    "korean": "트레이너가 포켓몬에게 흔들흔들댄스를 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Teeter Dance.",
    "targetForm": "흔들흔들댄스",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:브레이즈킥",
    "korean": "친구의 포켓몬이 브레이즈킥을 잘 써요.",
    "gloss": "My friend's Pokémon uses Blaze Kick well.",
    "targetForm": "브레이즈킥",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:흙놀이",
    "korean": "흙놀이는 전기 기술을 약하게 하는 기술이에요.",
    "gloss": "Mud Sport is a move that weakens Electric-type moves.",
    "targetForm": "흙놀이",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "mt_moon",
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:아이스볼",
    "korean": "체육관 시합에서 아이스볼을 사용했어요.",
    "gloss": "I used Ice Ball in the gym match.",
    "targetForm": "아이스볼",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:바늘팔",
    "korean": "기술 목록에 바늘팔이 있어요.",
    "gloss": "Needle Arm is on the move list.",
    "targetForm": "바늘팔",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:태만함",
    "korean": "포켓몬이 시합에서 태만함을 보여 줬어요.",
    "gloss": "The Pokémon showed off Slack Off in the match.",
    "targetForm": "태만함",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:하이퍼보이스",
    "korean": "하이퍼보이스는 트레이너의 자랑이에요.",
    "gloss": "Hyper Voice is the trainer's pride.",
    "targetForm": "하이퍼보이스",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:독엄니",
    "korean": "친구가 독엄니를 처음 봤어요.",
    "gloss": "My friend saw Poison Fang for the first time.",
    "targetForm": "독엄니",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:브레이크크루",
    "korean": "이 포켓몬은 브레이크크루를 익히는 중이에요.",
    "gloss": "This Pokémon is learning Crush Claw.",
    "targetForm": "브레이크크루",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:블러스트번",
    "korean": "포켓몬이 블러스트번을 사용했어요.",
    "gloss": "The Pokémon used Blast Burn.",
    "targetForm": "블러스트번",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:하이드로캐논",
    "korean": "선배가 하이드로캐논의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Hydro Cannon.",
    "targetForm": "하이드로캐논",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:코멧펀치",
    "korean": "포켓몬이 코멧펀치를 배웠어요.",
    "gloss": "The Pokémon learned Meteor Mash.",
    "targetForm": "코멧펀치",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_6",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_6"
    ]
  },
  {
    "vocabId": "rom-mine-v3:놀래키기",
    "korean": "트레이너가 포켓몬에게 놀래키기를 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Astonish.",
    "targetForm": "놀래키기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:웨더볼",
    "korean": "친구의 포켓몬이 웨더볼을 잘 써요.",
    "gloss": "My friend's Pokémon uses Weather Ball well.",
    "targetForm": "웨더볼",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:아로마테라피",
    "korean": "아로마테라피는 포켓몬의 상태 이상을 치료하는 기술이에요.",
    "gloss": "Aromatherapy is a move that heals a Pokémon's status conditions.",
    "targetForm": "아로마테라피",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:거짓울음",
    "korean": "체육관 시합에서 거짓울음을 사용했어요.",
    "gloss": "I used Fake Tears in the gym match.",
    "targetForm": "거짓울음",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:에어컷터",
    "korean": "기술 목록에 에어컷터가 있어요.",
    "gloss": "Air Cutter is on the move list.",
    "targetForm": "에어컷터",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "mt_moon",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "mt_moon"
    ]
  },
  {
    "vocabId": "rom-mine-v3:오버히트",
    "korean": "포켓몬이 시합에서 오버히트를 보여 줬어요.",
    "gloss": "The Pokémon showed off Overheat in the match.",
    "targetForm": "오버히트",
    "areaId": "rocket_hideout",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rocket_hideout",
    "areasReferenced": [
      "rocket_hideout"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:냄새구별",
    "korean": "냄새구별은 트레이너의 자랑이에요.",
    "gloss": "Odor Sleuth is the trainer's pride.",
    "targetForm": "냄새구별",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "pewter_city",
      "route_23"
    ]
  },
  {
    "vocabId": "rom-mine-v3:암석봉인",
    "korean": "친구가 암석봉인을 처음 봤어요.",
    "gloss": "My friend saw Rock Tomb for the first time.",
    "targetForm": "암석봉인",
    "areaId": "mt_moon",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "mt_moon",
    "areasReferenced": [
      "mt_moon"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:은빛바람",
    "korean": "이 포켓몬은 은빛바람을 익히는 중이에요.",
    "gloss": "This Pokémon is learning Silver Wind.",
    "targetForm": "은빛바람",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_24",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_12",
      "route_24"
    ]
  },
  {
    "vocabId": "rom-mine-v3:금속음",
    "korean": "포켓몬이 금속음을 사용했어요.",
    "gloss": "The Pokémon used Metal Sound.",
    "targetForm": "금속음",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "mt_moon",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined",
      "cinnabar_island",
      "mt_moon"
    ],
    "liveRecIds": [
      7328
    ]
  },
  {
    "vocabId": "rom-mine-v3:풀피리",
    "korean": "선배가 풀피리의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Grass Whistle.",
    "targetForm": "풀피리",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      5203
    ]
  },
  {
    "vocabId": "rom-mine-v3:간지르기",
    "korean": "포켓몬이 간지르기를 배웠어요.",
    "gloss": "The Pokémon learned Tickle.",
    "targetForm": "간지르기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:코스믹파워",
    "korean": "트레이너가 포켓몬에게 코스믹파워를 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Cosmic Power.",
    "targetForm": "코스믹파워",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_6",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "fuchsia_city",
      "route_6"
    ]
  },
  {
    "vocabId": "rom-mine-v3:바지락조개",
    "korean": "친구의 포켓몬이 바지락조개를 잘 써요.",
    "gloss": "My friend's Pokémon uses Water Spout well.",
    "targetForm": "바지락조개",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7332
    ]
  },
  {
    "vocabId": "rom-mine-v3:시그널빔",
    "korean": "시그널빔은 포켓몬이 시합에서 쓰는 기술이에요.",
    "gloss": "Signal Beam is a move Pokémon use in battle.",
    "targetForm": "시그널빔",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:섀도펀치",
    "korean": "체육관 시합에서 섀도펀치를 사용했어요.",
    "gloss": "I used Shadow Punch in the gym match.",
    "targetForm": "섀도펀치",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "vermilion_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "vermilion_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:신통력",
    "korean": "기술 목록에 신통력이 있어요.",
    "gloss": "Extrasensory is on the move list.",
    "targetForm": "신통력",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7335
    ]
  },
  {
    "vocabId": "rom-mine-v3:스카이업퍼",
    "korean": "포켓몬이 시합에서 스카이업퍼를 보여 줬어요.",
    "gloss": "The Pokémon showed off Sky Uppercut in the match.",
    "targetForm": "스카이업퍼",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "saffron_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "saffron_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:모래지옥",
    "korean": "모래지옥은 트레이너의 자랑이에요.",
    "gloss": "Sand Tomb is the trainer's pride.",
    "targetForm": "모래지옥",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_4",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_4"
    ]
  },
  {
    "vocabId": "rom-mine-v3:절대영도",
    "korean": "친구가 절대영도를 처음 봤어요.",
    "gloss": "My friend saw Sheer Cold for the first time.",
    "targetForm": "절대영도",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "silph_co",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "seafoam_islands",
      "silph_co"
    ]
  },
  {
    "vocabId": "rom-mine-v3:탁류",
    "korean": "이 포켓몬은 탁류를 익히는 중이에요.",
    "gloss": "This Pokémon is learning Muddy Water.",
    "targetForm": "탁류",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7339
    ]
  },
  {
    "vocabId": "rom-mine-v3:기관총",
    "korean": "포켓몬이 기관총을 사용했어요.",
    "gloss": "The Pokémon used Bullet Seed.",
    "targetForm": "기관총",
    "areaId": "cerulean_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "cerulean_city",
    "areasReferenced": [
      "cerulean_city",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      7340
    ]
  },
  {
    "vocabId": "rom-mine-v3:제비반환",
    "korean": "선배가 제비반환의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Aerial Ace.",
    "targetForm": "제비반환",
    "areaId": "fuchsia_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "fuchsia_city",
    "areasReferenced": [
      "fuchsia_city"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:고드름침",
    "korean": "포켓몬이 고드름침을 배웠어요.",
    "gloss": "The Pokémon learned Icicle Spear.",
    "targetForm": "고드름침",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:철벽",
    "korean": "트레이너가 포켓몬에게 철벽을 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Iron Defense.",
    "targetForm": "철벽",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7343
    ]
  },
  {
    "vocabId": "rom-mine-v3:블록",
    "korean": "친구의 포켓몬이 블록을 잘 써요.",
    "gloss": "My friend's Pokémon uses Block well.",
    "targetForm": "블록",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_12",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined",
      "route_12"
    ],
    "liveRecIds": [
      7344
    ]
  },
  {
    "vocabId": "rom-mine-v3:멀리짖음",
    "korean": "멀리짖음은 공격력을 올리는 기술이에요.",
    "gloss": "Howl is a move that raises Attack.",
    "targetForm": "멀리짖음",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:드래곤크루",
    "korean": "체육관 시합에서 드래곤크루를 사용했어요.",
    "gloss": "I used Dragon Claw in the gym match.",
    "targetForm": "드래곤크루",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:하드플랜트",
    "korean": "기술 목록에 하드플랜트가 있어요.",
    "gloss": "Frenzy Plant is on the move list.",
    "targetForm": "하드플랜트",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:벌크업",
    "korean": "포켓몬이 시합에서 벌크업을 보여 줬어요.",
    "gloss": "The Pokémon showed off Bulk Up in the match.",
    "targetForm": "벌크업",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:뛰어오르다",
    "korean": "'뛰어오르다'라는 기술은 트레이너의 자랑이에요.",
    "gloss": "Bounce is the trainer's pride.",
    "targetForm": "뛰어오르다",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "auditFix": {
      "verdict": "polish:fix",
      "issue": "Same parse collision as 깨트리다는: 뛰어오르다 is a verb in dictionary form, and attaching 는 produces what reads as a malformed quotative -다는 rather than topic-marking a noun. Use the (이)라는 naming particle to cite the move name as a name.",
      "evidenceUrl": "https://123learnkorean.wordpress.com/2009/08/25/%EC%9D%B4%EB%9D%BC%EB%8A%94-called/",
      "auditedAt": "2026-05-09"
    },
    "firstAreaEncountered": "fuchsia_city",
    "areasReferenced": [
      "rom_mined",
      "fuchsia_city"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      5182
    ]
  },
  {
    "vocabId": "rom-mine-v3:머드숏",
    "korean": "친구가 머드숏을 처음 봤어요.",
    "gloss": "My friend saw Mud Shot for the first time.",
    "targetForm": "머드숏",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "pallet_town"
    ]
  },
  {
    "vocabId": "rom-mine-v3:포이즌테일",
    "korean": "이 포켓몬은 포이즌테일을 익히는 중이에요.",
    "gloss": "This Pokémon is learning Poison Tail.",
    "targetForm": "포이즌테일",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:탐내다",
    "korean": "친구의 포켓몬이 '탐내다'를 썼어요.",
    "gloss": "My friend's Pokémon used Covet.",
    "targetForm": "탐내다",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "auditFix": {
      "verdict": "polish:fix",
      "issue": "Confirmed broken: 탐내다가 parses as the connective -다가 ('while coveting...'), giving 'while coveting, it echoed across the field' — nonsensical. The fix cites the move name with the 라는 naming particle and uses 기술이 as the actual subject of 울려 퍼지다.",
      "evidenceUrl": "https://123learnkorean.wordpress.com/2009/08/25/%EC%9D%B4%EB%9D%BC%EB%8A%94-called/",
      "auditedAt": "2026-05-09"
    },
    "firstAreaEncountered": "route_12",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "rom_mined",
      "route_12"
    ],
    "liveRecIds": [
      7351
    ]
  },
  {
    "vocabId": "rom-mine-v3:볼트태클",
    "korean": "선배가 볼트태클의 사용법을 알려 줬어요.",
    "gloss": "A senior taught me how to use Volt Tackle.",
    "targetForm": "볼트태클",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:메지컬리프",
    "korean": "포켓몬이 메지컬리프를 배웠어요.",
    "gloss": "The Pokémon learned Magical Leaf.",
    "targetForm": "메지컬리프",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:물놀이",
    "korean": "트레이너가 포켓몬에게 물놀이를 가르쳤어요.",
    "gloss": "The trainer taught the Pokémon Water Sport.",
    "targetForm": "물놀이",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "viridian_city",
    "areasReferenced": [
      "rom_mined",
      "pewter_city",
      "viridian_city"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      5265
    ]
  },
  {
    "vocabId": "rom-mine-v3:명상",
    "korean": "친구의 포켓몬이 명상을 잘 써요.",
    "gloss": "My friend's Pokémon uses Calm Mind well.",
    "targetForm": "명상",
    "areaId": "saffron_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "saffron_city",
    "areasReferenced": [
      "saffron_city",
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      2726
    ]
  },
  {
    "vocabId": "rom-mine-v3:리프블레이드",
    "korean": "리프블레이드는 포켓몬이 시합에서 쓰는 기술이에요.",
    "gloss": "Leaf Blade is a move Pokémon use in battle.",
    "targetForm": "리프블레이드",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:용의춤",
    "korean": "체육관 시합에서 용의춤을 사용했어요.",
    "gloss": "I used Dragon Dance in the gym match.",
    "targetForm": "용의춤",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "pallet_town"
    ]
  },
  {
    "vocabId": "rom-mine-v3:락블레스트",
    "korean": "기술 목록에 락블레스트가 있어요.",
    "gloss": "Rock Blast is on the move list.",
    "targetForm": "락블레스트",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "mt_moon",
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:전격파",
    "korean": "포켓몬이 시합에서 전격파를 보여 줬어요.",
    "gloss": "The Pokémon showed off Shock Wave in the match.",
    "targetForm": "전격파",
    "areaId": "rocket_hideout",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rocket_hideout",
    "areasReferenced": [
      "rocket_hideout"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:물의파동",
    "korean": "물의파동은 트레이너의 자랑이에요.",
    "gloss": "Water Pulse is the trainer's pride.",
    "targetForm": "물의파동",
    "areaId": "celadon_city",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "celadon_city",
    "areasReferenced": [
      "celadon_city"
    ],
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move"
  },
  {
    "vocabId": "rom-mine-v3:파멸의소원",
    "korean": "친구가 파멸의소원을 처음 봤어요.",
    "gloss": "My friend saw Doom Desire for the first time.",
    "targetForm": "파멸의소원",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:사이코부스트",
    "korean": "이 포켓몬은 사이코부스트를 익히는 중이에요.",
    "gloss": "This Pokémon is learning Psycho Boost.",
    "targetForm": "사이코부스트",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:악취",
    "korean": "이 포켓몬은 악취 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Stench ability.",
    "targetForm": "악취",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "celadon_city",
    "areasReferenced": [
      "rom_mined",
      "celadon_city"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      5248
    ]
  },
  {
    "vocabId": "rom-mine-v3:잔비",
    "korean": "잔비는 보기 드문 특성이에요.",
    "gloss": "Drizzle is a rare ability.",
    "targetForm": "잔비",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7364
    ]
  },
  {
    "vocabId": "rom-mine-v3:가속",
    "korean": "도감에서 가속의 설명을 읽었어요.",
    "gloss": "I read about Speed Boost in the encyclopedia.",
    "targetForm": "가속",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7365
    ]
  },
  {
    "vocabId": "rom-mine-v3:전투무장",
    "korean": "이 포켓몬은 전투무장 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Battle Armor Ability.",
    "targetForm": "전투무장",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "cerulean_city",
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:옹골참",
    "korean": "옹골참 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Sturdy ability helped a lot in the match.",
    "targetForm": "옹골참",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "cinnabar_island",
      "mt_moon",
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:습기",
    "korean": "연구원이 습기에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Damp.",
    "targetForm": "습기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pallet_town",
      "pewter_city",
      "viridian_city"
    ],
    "liveRecIds": [
      7368
    ]
  },
  {
    "vocabId": "rom-mine-v3:유연",
    "korean": "유연을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Limber are easy to handle.",
    "targetForm": "유연",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "mt_moon",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "mt_moon"
    ],
    "liveRecIds": [
      5154
    ]
  },
  {
    "vocabId": "rom-mine-v3:모래숨기",
    "korean": "새로운 모래숨기 특성을 알게 됐어요.",
    "gloss": "I learned about a new Sand Veil ability.",
    "targetForm": "모래숨기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_1",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "mt_moon",
      "pewter_city",
      "route_1",
      "route_4"
    ]
  },
  {
    "vocabId": "rom-mine-v3:정전기",
    "korean": "이 포켓몬은 정전기 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Static ability.",
    "targetForm": "정전기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "areasReferenced": [
      "rom_mined",
      "pallet_town",
      "power_plant",
      "route_10",
      "viridian_city"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      5107
    ]
  },
  {
    "vocabId": "rom-mine-v3:축전",
    "korean": "축전은 보기 드문 특성이에요.",
    "gloss": "Volt Absorb is a rare ability.",
    "targetForm": "축전",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7372
    ]
  },
  {
    "vocabId": "rom-mine-v3:저수",
    "korean": "도감에서 저수의 설명을 읽었어요.",
    "gloss": "I read about Water Absorb in the encyclopedia.",
    "targetForm": "저수",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "viridian_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "silph_co",
      "viridian_city"
    ],
    "liveRecIds": [
      7373
    ]
  },
  {
    "vocabId": "rom-mine-v3:둔감",
    "korean": "이 포켓몬은 둔감 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Oblivious Ability.",
    "targetForm": "둔감",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "cinnabar_island",
      "pallet_town"
    ],
    "liveRecIds": [
      7374
    ]
  },
  {
    "vocabId": "rom-mine-v3:날씨부정",
    "korean": "날씨부정 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Cloud Nine ability helped a lot in the match.",
    "targetForm": "날씨부정",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:복안",
    "korean": "연구원이 복안에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Compound Eyes.",
    "targetForm": "복안",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_24",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_24"
    ],
    "liveRecIds": [
      7376
    ]
  },
  {
    "vocabId": "rom-mine-v3:불면",
    "korean": "불면을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Insomnia are easy to handle.",
    "targetForm": "불면",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "lavender_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "lavender_town",
      "route_12",
      "route_13",
      "route_14",
      "route_15"
    ],
    "liveRecIds": [
      1479,
      6631,
      6632,
      6823
    ]
  },
  {
    "vocabId": "rom-mine-v3:변색",
    "korean": "새로운 변색 특성을 알게 됐어요.",
    "gloss": "I learned about a new Color Change ability.",
    "targetForm": "변색",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7378
    ]
  },
  {
    "vocabId": "rom-mine-v3:면역",
    "korean": "이 포켓몬은 면역 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Immunity ability.",
    "targetForm": "면역",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_12",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_12"
    ],
    "liveRecIds": [
      7379
    ]
  },
  {
    "vocabId": "rom-mine-v3:타오르는불꽃",
    "korean": "타오르는불꽃은 보기 드문 특성이에요.",
    "gloss": "Flash Fire is a rare ability.",
    "targetForm": "타오르는불꽃",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_7",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "fuchsia_city",
      "route_23",
      "route_7"
    ]
  },
  {
    "vocabId": "rom-mine-v3:인분",
    "korean": "도감에서 인분의 설명을 읽었어요.",
    "gloss": "I read about Shield Dust in the encyclopedia.",
    "targetForm": "인분",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_12",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_12"
    ],
    "liveRecIds": [
      7381
    ]
  },
  {
    "vocabId": "rom-mine-v3:마이페이스",
    "korean": "이 포켓몬은 마이페이스 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Own Tempo Ability.",
    "targetForm": "마이페이스",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "cinnabar_island",
      "pallet_town"
    ]
  },
  {
    "vocabId": "rom-mine-v3:흡반",
    "korean": "흡반 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Suction Cups ability helped a lot in the match.",
    "targetForm": "흡반",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "mt_moon",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "mt_moon"
    ],
    "liveRecIds": [
      7383
    ]
  },
  {
    "vocabId": "rom-mine-v3:위협",
    "korean": "연구원이 위협에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Intimidate.",
    "targetForm": "위협",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "areasReferenced": [
      "rom_mined",
      "pallet_town",
      "pewter_city",
      "route_23"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      5140
    ]
  },
  {
    "vocabId": "rom-mine-v3:그림자밟기",
    "korean": "그림자밟기를 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Shadow Tag are easy to handle.",
    "targetForm": "그림자밟기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "mt_moon",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "mt_moon"
    ],
    "liveRecIds": [
      7385
    ]
  },
  {
    "vocabId": "rom-mine-v3:까칠한피부",
    "korean": "새로운 까칠한피부 특성을 알게 됐어요.",
    "gloss": "I learned about a new Rough Skin ability.",
    "targetForm": "까칠한피부",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:불가사의부적",
    "korean": "이 포켓몬은 불가사의부적 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Wonder Guard ability.",
    "targetForm": "불가사의부적",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:부유",
    "korean": "부유는 보기 드문 특성이에요.",
    "gloss": "Levitate is a rare ability.",
    "targetForm": "부유",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "vermilion_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "celadon_city",
      "vermilion_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:포자",
    "korean": "도감에서 포자의 설명을 읽었어요.",
    "gloss": "I read about Effect Spore in the encyclopedia.",
    "targetForm": "포자",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:싱크로",
    "korean": "이 포켓몬은 싱크로 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Synchronize Ability.",
    "targetForm": "싱크로",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_24",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_24",
      "route_25"
    ],
    "liveRecIds": [
      7390
    ]
  },
  {
    "vocabId": "rom-mine-v3:클리어바디",
    "korean": "클리어바디 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Clear Body ability helped a lot in the match.",
    "targetForm": "클리어바디",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "auditFix": {
      "verdict": "ungrammatical",
      "issue": "Wrong subject particle. 특성 ends in the consonant ㅇ (받침), so it must take 이, not 가. '특성가' is ungrammatical.",
      "evidenceUrl": null,
      "auditedAt": "2026-05-09"
    },
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pallet_town"
    ]
  },
  {
    "vocabId": "rom-mine-v3:자연회복",
    "korean": "연구원이 자연회복에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Natural Cure.",
    "targetForm": "자연회복",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "fuchsia_city",
      "pallet_town",
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:피뢰침",
    "korean": "피뢰침을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Lightning Rod are easy to handle.",
    "targetForm": "피뢰침",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "viridian_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "cerulean_city",
      "pewter_city",
      "viridian_city"
    ],
    "liveRecIds": [
      7393
    ]
  },
  {
    "vocabId": "rom-mine-v3:하늘의은총",
    "korean": "새로운 하늘의은총 특성을 알게 됐어요.",
    "gloss": "I learned about a new Serene Grace ability.",
    "targetForm": "하늘의은총",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pewter_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:쓱쓱",
    "korean": "이 포켓몬은 쓱쓱 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Swift Swim ability.",
    "targetForm": "쓱쓱",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "viridian_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pewter_city",
      "route_2",
      "viridian_city"
    ],
    "liveRecIds": [
      7395
    ]
  },
  {
    "vocabId": "rom-mine-v3:엽록소",
    "korean": "엽록소는 보기 드문 특성이에요.",
    "gloss": "Chlorophyll is a rare ability.",
    "targetForm": "엽록소",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pallet_town",
      "route_12",
      "route_24"
    ],
    "liveRecIds": [
      7396
    ]
  },
  {
    "vocabId": "rom-mine-v3:발광",
    "korean": "도감에서 발광의 설명을 읽었어요.",
    "gloss": "I read about Illuminate in the encyclopedia.",
    "targetForm": "발광",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "fuchsia_city",
      "pallet_town"
    ],
    "liveRecIds": [
      7397
    ]
  },
  {
    "vocabId": "rom-mine-v3:트레이스",
    "korean": "이 포켓몬은 트레이스 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Trace Ability.",
    "targetForm": "트레이스",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "celadon_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "celadon_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:천하장사",
    "korean": "천하장사 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Huge Power ability helped a lot in the match.",
    "targetForm": "천하장사",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "auditFix": {
      "verdict": "ungrammatical",
      "issue": "Wrong subject particle. 특성 ends in a consonant (받침 ㅇ) and must take 이. '특성가' is ungrammatical.",
      "evidenceUrl": null,
      "auditedAt": "2026-05-09"
    },
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      5142
    ]
  },
  {
    "vocabId": "rom-mine-v3:독가시",
    "korean": "연구원이 독가시에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Poison Point.",
    "targetForm": "독가시",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pallet_town",
      "route_3"
    ]
  },
  {
    "vocabId": "rom-mine-v3:정신력",
    "korean": "정신력을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Inner Focus are easy to handle.",
    "targetForm": "정신력",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "areasReferenced": [
      "rom_mined",
      "pewter_city",
      "route_11",
      "route_21",
      "route_24",
      "route_25",
      "saffron_city"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      2729
    ]
  },
  {
    "vocabId": "rom-mine-v3:마그마의무장",
    "korean": "새로운 마그마의무장 특성을 알게 됐어요.",
    "gloss": "I learned about a new Magma Armor ability.",
    "targetForm": "마그마의무장",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:수의베일",
    "korean": "이 포켓몬은 수의베일 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Water Veil ability.",
    "targetForm": "수의베일",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "viridian_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "viridian_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:자력",
    "korean": "자력은 보기 드문 특성이에요.",
    "gloss": "Magnet Pull is a rare ability.",
    "targetForm": "자력",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "cinnabar_island",
    "areasReferenced": [
      "rom_mined",
      "cinnabar_island"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      5307
    ]
  },
  {
    "vocabId": "rom-mine-v3:방음",
    "korean": "도감에서 방음의 설명을 읽었어요.",
    "gloss": "I read about Soundproof in the encyclopedia.",
    "targetForm": "방음",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pallet_town",
      "route_10"
    ],
    "liveRecIds": [
      7405
    ]
  },
  {
    "vocabId": "rom-mine-v3:젖은접시",
    "korean": "이 포켓몬은 젖은접시 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Rain Dish Ability.",
    "targetForm": "젖은접시",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pallet_town"
    ]
  },
  {
    "vocabId": "rom-mine-v3:모래날림",
    "korean": "모래날림 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Sand Stream ability helped a lot in the match.",
    "targetForm": "모래날림",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:프레셔",
    "korean": "연구원이 프레셔에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Pressure.",
    "targetForm": "프레셔",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "cerulean_cave",
      "pewter_city",
      "power_plant",
      "route_23",
      "seafoam_islands"
    ]
  },
  {
    "vocabId": "rom-mine-v3:두꺼운지방",
    "korean": "두꺼운지방을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Thick Fat are easy to handle.",
    "targetForm": "두꺼운지방",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_12",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "route_12"
    ]
  },
  {
    "vocabId": "rom-mine-v3:일찍기상",
    "korean": "새로운 일찍기상 특성을 알게 됐어요.",
    "gloss": "I learned about a new Early Bird ability.",
    "targetForm": "일찍기상",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_16",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "route_16",
      "route_21"
    ]
  },
  {
    "vocabId": "rom-mine-v3:불꽃몸",
    "korean": "이 포켓몬은 불꽃몸 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Flame Body ability.",
    "targetForm": "불꽃몸",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "fuchsia_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "fuchsia_city",
      "route_23"
    ]
  },
  {
    "vocabId": "rom-mine-v3:도주",
    "korean": "도주는 보기 드문 특성이에요.",
    "gloss": "Run Away is a rare ability.",
    "targetForm": "도주",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "fuchsia_city",
      "pallet_town",
      "route_1",
      "route_13",
      "route_16",
      "route_2"
    ],
    "liveRecIds": [
      7412
    ]
  },
  {
    "vocabId": "rom-mine-v3:날카로운눈",
    "korean": "도감에서 날카로운눈의 설명을 읽었어요.",
    "gloss": "I read about Keen Eye in the encyclopedia.",
    "targetForm": "날카로운눈",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_1",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "mt_moon",
      "route_1",
      "route_13",
      "route_16",
      "route_3",
      "saffron_city"
    ]
  },
  {
    "vocabId": "rom-mine-v3:괴력집게",
    "korean": "이 포켓몬은 괴력집게 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Hyper Cutter Ability.",
    "targetForm": "괴력집게",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pallet_town"
    ]
  },
  {
    "vocabId": "rom-mine-v3:픽업",
    "korean": "픽업 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Pickup ability helped a lot in the match.",
    "targetForm": "픽업",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_6",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_6"
    ],
    "liveRecIds": [
      7415
    ]
  },
  {
    "vocabId": "rom-mine-v3:게으름",
    "korean": "연구원이 게으름에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Truant.",
    "targetForm": "게으름",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      1000
    ]
  },
  {
    "vocabId": "rom-mine-v3:의욕",
    "korean": "의욕을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Hustle are easy to handle.",
    "targetForm": "의욕",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_1",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "mt_moon",
      "route_1",
      "route_2",
      "route_3"
    ]
  },
  {
    "vocabId": "rom-mine-v3:헤롱헤롱바디",
    "korean": "새로운 헤롱헤롱바디 특성을 알게 됐어요.",
    "gloss": "I learned about a new Cute Charm ability.",
    "targetForm": "헤롱헤롱바디",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_3",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "route_3",
      "route_6"
    ]
  },
  {
    "vocabId": "rom-mine-v3:플러스",
    "korean": "이 포켓몬은 플러스 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Plus ability.",
    "targetForm": "플러스",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text",
      "item_description"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      2310
    ]
  },
  {
    "vocabId": "rom-mine-v3:마이너스",
    "korean": "마이너스는 보기 드문 특성이에요.",
    "gloss": "Minus is a rare ability.",
    "targetForm": "마이너스",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:기분파",
    "korean": "도감에서 기분파의 설명을 읽었어요.",
    "gloss": "I read about Forecast in the encyclopedia.",
    "targetForm": "기분파",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "areasReferenced": [
      "rom_mined"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      3949
    ]
  },
  {
    "vocabId": "rom-mine-v3:점착",
    "korean": "이 포켓몬은 점착 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Sticky Hold Ability.",
    "targetForm": "점착",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "celadon_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "celadon_city"
    ],
    "liveRecIds": [
      7422
    ]
  },
  {
    "vocabId": "rom-mine-v3:탈피",
    "korean": "탈피 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Shed Skin ability helped a lot in the match.",
    "targetForm": "탈피",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "auditFix": {
      "verdict": "ungrammatical",
      "issue": "Wrong subject particle. 특성 ends in a consonant (받침 ㅇ) and must take 이. '특성가' is ungrammatical.",
      "evidenceUrl": null,
      "auditedAt": "2026-05-09"
    },
    "firstAreaEncountered": "route_2",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pewter_city",
      "route_2"
    ],
    "liveRecIds": [
      7423
    ]
  },
  {
    "vocabId": "rom-mine-v3:근성",
    "korean": "연구원이 근성에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Guts.",
    "targetForm": "근성",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_1",
    "areasReferenced": [
      "rom_mined",
      "cerulean_city",
      "route_1",
      "route_2"
    ],
    "sourceTypes": [
      "pokemon_ability",
      "system_text"
    ],
    "primarySourceType": "pokemon_ability",
    "liveRecIds": [
      5228
    ]
  },
  {
    "vocabId": "rom-mine-v3:이상한비늘",
    "korean": "이상한비늘을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Marvel Scale are easy to handle.",
    "targetForm": "이상한비늘",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:해감액",
    "korean": "새로운 해감액 특성을 알게 됐어요.",
    "gloss": "I learned about a new Liquid Ooze ability.",
    "targetForm": "해감액",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pallet_town"
    ]
  },
  {
    "vocabId": "rom-mine-v3:심록",
    "korean": "이 포켓몬은 심록 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Overgrow ability.",
    "targetForm": "심록",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pallet_town"
    ],
    "liveRecIds": [
      7427
    ]
  },
  {
    "vocabId": "rom-mine-v3:맹화",
    "korean": "맹화는 보기 드문 특성이에요.",
    "gloss": "Blaze is a rare ability.",
    "targetForm": "맹화",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pallet_town"
    ],
    "liveRecIds": [
      7428
    ]
  },
  {
    "vocabId": "rom-mine-v3:급류",
    "korean": "도감에서 급류의 설명을 읽었어요.",
    "gloss": "I read about Torrent in the encyclopedia.",
    "targetForm": "급류",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "pallet_town"
    ],
    "liveRecIds": [
      7429
    ]
  },
  {
    "vocabId": "rom-mine-v3:벌레의알림",
    "korean": "이 포켓몬은 벌레의알림 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the Swarm Ability.",
    "targetForm": "벌레의알림",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_24",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "route_24"
    ]
  },
  {
    "vocabId": "rom-mine-v3:돌머리",
    "korean": "돌머리 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Rock Head ability helped a lot in the match.",
    "targetForm": "돌머리",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "auditFix": {
      "verdict": "ungrammatical",
      "issue": "Wrong subject particle. 특성 ends in a consonant (받침 ㅇ) and must take 이. '특성가' is ungrammatical.",
      "evidenceUrl": null,
      "auditedAt": "2026-05-09"
    },
    "firstAreaEncountered": "pewter_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "cerulean_city",
      "mt_moon",
      "pewter_city"
    ],
    "liveRecIds": [
      7430
    ]
  },
  {
    "vocabId": "rom-mine-v3:가뭄",
    "korean": "연구원이 가뭄에 대해 설명해 줬어요.",
    "gloss": "The researcher explained Drought.",
    "targetForm": "가뭄",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_7",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_7"
    ],
    "liveRecIds": [
      7431
    ]
  },
  {
    "vocabId": "rom-mine-v3:개미지옥",
    "korean": "개미지옥을 가진 포켓몬은 다루기가 쉬워요.",
    "gloss": "Pokémon with Arena Trap are easy to handle.",
    "targetForm": "개미지옥",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_1",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_1"
    ],
    "liveRecIds": [
      7432
    ]
  },
  {
    "vocabId": "rom-mine-v3:의기양양",
    "korean": "새로운 의기양양 특성을 알게 됐어요.",
    "gloss": "I learned about a new Vital Spirit ability.",
    "targetForm": "의기양양",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "viridian_city",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined",
      "route_3",
      "viridian_city"
    ],
    "liveRecIds": [
      7433
    ]
  },
  {
    "vocabId": "rom-mine-v3:하얀연기",
    "korean": "이 포켓몬은 하얀연기 특성을 가지고 있어요.",
    "gloss": "This Pokémon has the White Smoke ability.",
    "targetForm": "하얀연기",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:순수한힘",
    "korean": "순수한힘은 보기 드문 특성이에요.",
    "gloss": "Pure Power is a rare ability.",
    "targetForm": "순수한힘",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": []
  },
  {
    "vocabId": "rom-mine-v3:조가비갑옷",
    "korean": "도감에서 조가비갑옷의 설명을 읽었어요.",
    "gloss": "I read about Shell Armor in the encyclopedia.",
    "targetForm": "조가비갑옷",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "pallet_town",
      "silph_co"
    ]
  },
  {
    "vocabId": "rom-mine-v3:소음",
    "korean": "소음은 어떤 포켓몬도 실제로 지니지 않는 특성이에요.",
    "gloss": "Cacophony is an Ability that no Pokémon actually has.",
    "targetForm": "소음",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7437
    ]
  },
  {
    "vocabId": "rom-mine-v3:에어록",
    "korean": "에어록 특성이 시합에서 큰 도움이 됐어요.",
    "gloss": "The Air Lock ability helped a lot in the match.",
    "targetForm": "에어록",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "rom_mined",
    "sourceTypes": [
      "pokemon_ability"
    ],
    "primarySourceType": "pokemon_ability",
    "areasReferenced": [
      "rom_mined"
    ],
    "liveRecIds": [
      7438
    ]
  },
  {
    "vocabId": "rom-mine-v3:속이다",
    "korean": "포켓몬이 '속이다'를 쓰자 상대가 움찔했어요.",
    "gloss": "When the Pokémon used Fake Out, the opponent flinched.",
    "targetForm": "속이다",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "route_24",
    "sourceTypes": [
      "pokemon_move"
    ],
    "primarySourceType": "pokemon_move",
    "areasReferenced": [
      "route_24",
      "saffron_city",
      "vermilion_city",
      "fuchsia_city",
      "cinnabar_island",
      "celadon_city",
      "indigo_plateau",
      "rom_mined"
    ],
    "liveRecIds": [
      1103,
      4935,
      6102
    ]
  },
  {
    "vocabId": "rom-mine-v3:돌진",
    "korean": "포켓몬이 돌진 기술로 적을 밀어냈어요.",
    "gloss": "The Pokémon used Take Down to push back the foe.",
    "targetForm": "돌진",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "pallet_town",
    "areasReferenced": [
      "rom_mined",
      "fuchsia_city",
      "pallet_town",
      "pewter_city",
      "route_13",
      "route_23"
    ],
    "sourceTypes": [
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      121
    ]
  },
  {
    "vocabId": "rom-mine-v3:방어",
    "korean": "친구가 방어 기술을 처음 가르쳐 줬어요.",
    "gloss": "My friend first taught me the Protect move.",
    "targetForm": "방어",
    "areaId": "rom_mined",
    "source": "themed-v1",
    "generator": "llm-claude-opus-4-7",
    "firstAreaEncountered": "fuchsia_city",
    "areasReferenced": [
      "fuchsia_city",
      "saffron_city",
      "celadon_city",
      "rom_mined"
    ],
    "sourceTypes": [
      "item_description",
      "pokemon_move",
      "system_text"
    ],
    "primarySourceType": "pokemon_move",
    "liveRecIds": [
      3720
    ]
  }
]
```
