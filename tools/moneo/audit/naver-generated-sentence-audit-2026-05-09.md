# Naver Generated Korean Sentence Audit - 2026-05-09

## Scope

Reviewed generator-tagged Korean sentence assets under `app/src/main/assets/moneo`.

- Total generator-tagged entries scanned: 1,988
- Generated sentence prose audited for naturalness: 1,846
  - `sentences-ko-study.json`: 45
  - `sentences-ko-species.json`: 246
  - `sentences-ko-themed.json`: 20
  - `sentences-ko-themed-mined.json`: 586
  - `sentences-ko-themed-species.json`: 241
  - `sentences-ko-themed-topik.json`: 708
- `sentences-ko-etymology.json`: 142 generated entries scanned structurally, but these are species-name examples rather than Korean sentence prose. They need a separate etymology/gloss audit, not sentence-naturalness edits.

## Naver CLI Evidence Used

Direct Naver searches and Naver Dictionary JSON calls were made from the CLI.

- Naver Dictionary `트다`: includes the dry/chapped sense, with example `나는 겨울만 되면 입술이 튼다.` This supports `입술이 텄어요` and rejects the prior wrong-lemma `트인 들판` example for the headword `트다`.
- Naver search `입술이 텄어요 트다`: returned common Korean health/usage results around `입술이 트다`.
- Naver search `"껍질에숨기"`: confirms `껍질에숨기` as a Pokemon move-name string; revision uses `껍질에숨기 기술` to avoid the awkward `껍질에숨기를` parse.
- Naver Dictionary `모습`: defines `모습` as a person's appearance/figure and outward shape, not specifically `얼굴`. This supports reglossing away from "face".
- Naver Dictionary `짓다`: first sense includes `밥을 짓다`, supporting the revised rice-cooking sentence.
- Naver Dictionary `삼월`: confirms `삼월` as the month name and example `벌써 꽃 피는 삼월이 되었다.` This supports no-space `삼월`.
- Naver Dictionary `쌀`: defines raw hulled rice, supporting a gloss that distinguishes `쌀` from cooked `밥`.
- Naver search `이상해풀 꽃봉오리 포켓몬`: returns Pokemon Wiki/Fandom text describing Ivysaur's back growth as `꽃봉오리`, supporting the species-lore correction.
- Naver searches `"야생의 피카츄가 나타났다"`, `"야생의 리자몽이 나타났다"`, and `"야생의 이상해씨가 나타났다"`: sanity-check the Pokemon encounter phrasing and the materialized `이/가` particle pattern.

## Applied Revisions

| File | Count | Issue | Revision |
| --- | ---: | --- | --- |
| `sentences-ko-species.json` | 246 | Templated `이(가)` produced blatantly incorrect Korean such as `이상해씨이(가) 나타났다!`. | Materialized the correct subject particle per final batchim and added battle-style `야생의`: `야생의 이상해씨가 나타났다!`, `야생의 이상해풀이 나타났다!`, etc. |
| `sentences-ko-themed-mined.json` | 1 | Pasted audit prose in Korean field for `rom-mine-v2:트다`, and the previous example used `트이다`, not `트다`. | `추운 동굴을 지나 입술이 텄어요.` |
| `sentences-ko-themed-mined.json` | 1 | Pasted audit prose in Korean field for `rom-mine-v2:껍질에숨기`; raw `껍질에숨기를` was awkward for learners. | `이 포켓몬은 껍질에숨기 기술을 익히는 중이에요.` |
| `sentences-ko-themed-topik.json` | 1 | Pasted audit prose in Korean field for `topik-v2:모습`; stale gloss treated `모습` as `face`. | `오랜만에 라이벌의 모습을 봤어요.` |
| `sentences-ko-themed-topik.json` | 1 | Pasted English sentence in Korean field for `topik-v2:짓다`; stale farmer/mother gloss mismatch. | `엄마가 여행길에 먹을 밥을 짓고 계세요.` |
| `sentences-ko-themed-topik.json` | 1 | Korean field contained an English alternative note for `topik-v2:월`. | `삼월에 태초마을을 떠나요.` |
| `sentences-ko-themed-topik.json` | 1 | Pasted English gloss text in Korean field for `topik-v2:쌀`. | `엄마가 쌀로 여행길에 먹을 밥을 지어요.` |
| `sentences-ko-themed.json` | 1 | Pasted audit prose in Korean field for `rom-species:이상해풀`; stale gloss said sprout instead of flower bud. | `이상해풀의 등에는 큰 꽃봉오리가 자라요.` |

## No-Change Review

`sentences-ko-study.json` was reviewed. The 45 entries are simple but grammatical, with no awkward or blatantly wrong Korean found in this pass.

The existing themed generated files were also re-scanned after the previous audit rounds. No remaining entries matched the known bad templates: `울려 퍼졌어요`, `도감에 ... 적혀`, `매우 강한 기술`, `첫 날`, `전화 번호`, `일 급`, `삼 월`, `오븐에 빵`, `자전거를 몰`, `손을 떨`, `Replace with`, `Reword to`, or `Update gloss`.

## Validation

Commands run after edits:

```bash
jq empty app/src/main/assets/moneo/sentences-ko-*.json
```

Additional generated-entry scans passed:

- No ASCII/editorial prose in generated Korean fields, excluding valid `PP`.
- No unresolved `이(가)`/`(가)` particle templates.
- No missing `targetForm` among generated sentence-prose assets.
- No matches for the suspicious-pattern scan listed above.
