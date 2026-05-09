# Korean Sentence Audit - 2026-05-09

## Scope

Audited generated Korean sentence assets used by Moneo:

- `app/src/main/assets/moneo/sentences-ko-themed-mined.json`
- `app/src/main/assets/moneo/sentences-ko-themed-species.json`
- `app/src/main/assets/moneo/sentences-ko-themed-topik.json`
- `app/src/main/assets/moneo/sentences-ko-themed.json`
- `app/src/main/assets/moneo/sentences-ko-study.json`

## Evidence Policy

Direct-source evidence only. I did not use Google AI answers, AI Overview text, or generated snippets as authority. For Korean usage, spacing, and collocation, I preferred Naver Korean Dictionary / Standard Korean Dictionary content surfaced through Naver. For Pokemon theming and species naming, I used official Pokemon Korea pages and the Korean LeafGreen/FireRed-oriented project assets.

## Direct Sources Consulted

- Naver Korean Dictionary, `미리`: https://ko.dict.naver.com/#/search?query=%EB%AF%B8%EB%A6%AC
  - Confirms `미리` means before something happens / in advance, which supports `약속 시간 전에 미리 도착했어요` over `약속 시간보다 미리...`.
- Naver Korean Dictionary, `일급`: https://ko.dict.naver.com/#/search?query=%EC%9D%BC%EA%B8%89
  - Confirms `일급` is a lexical item meaning highest/top class, not spaced as `일 급`.
- Naver Korean Dictionary, `불리다`: https://ko.dict.naver.com/#/search?query=%EB%B6%88%EB%A6%AC%EB%8B%A4
  - Used for passive naming/calling patterns such as `...이라고 불려요`.
- Naver Korean Dictionary, `전화번호`: https://ko.dict.naver.com/#/search?query=%EC%A0%84%ED%99%94%EB%B2%88%ED%98%B8
  - Used for spacing cleanup from `전화 번호` to `전화번호`.
- Naver Korean Dictionary, `사용하다`: https://ko.dict.naver.com/#/search?query=%EC%82%AC%EC%9A%A9%ED%95%98%EB%8B%A4
  - Used for natural `사용할 수 있어요` patterns.
- Naver Korean Dictionary, `복사하다`: https://ko.dict.naver.com/#/search?query=%EB%B3%B5%EC%82%AC%ED%95%98%EB%8B%A4
  - Used for natural transitive `서류를 복사하다` usage.
- Naver Korean Dictionary, `발견하다`: https://ko.dict.naver.com/#/search?query=%EB%B0%9C%EA%B2%AC%ED%95%98%EB%8B%A4
  - Used for natural `동굴을 발견했어요` usage over noun-heavy `발견을 했어요`.
- Naver Korean Dictionary, `공짜`: https://ko.dict.naver.com/#/search?query=%EA%B3%B5%EC%A7%9C
  - Used for `공짜로 들어갈 수 있어요` rather than the over-literal `공짜로 들어가요`.
- Official Pokemon Korea Pokedex: https://pokemonkorea.co.kr/pokedex
  - Used as the official Korean Pokemon naming/theming baseline.

## Applied Fix Summary

Changed 137 generated entries relative to the repository baseline.

| Category                              | Count | Representative Fix                                                                            |
| ------------------------------------- | ----: | --------------------------------------------------------------------------------------------- |
| Generic Pokemon templates             |    84 | `도감에 물대포가 적혀 있어요.` -> `기술 목록에 물대포가 있어요.`                              |
| Grammar / collocation                 |    25 | `잠자기 전에 불을 끔이 좋아요.` -> `잠자기 전에 불을 끄는 것이 좋아요.`                       |
| TOPIK spacing / numeral / collocation |     9 | `전화 번호 끝자리는 오예요.` -> `전화번호 끝자리는 오예요.`                                   |
| Target-form or gloss mismatch         |    15 | `동생이 곧 떠난다고 해요.` -> `동생이 갑자기 열이 났어요.`                                    |
| Species lore / Pokemon collocation    |     4 | `레어코일은 세 개의 자석으로 이루어졌어요.` -> `레어코일은 코일 세 마리가 모인 포켓몬이에요.` |

Per-file changed-entry counts:

| File                               | Changed Entries |
| ---------------------------------- | --------------: |
| `sentences-ko-themed-mined.json`   |             111 |
| `sentences-ko-themed-species.json` |               4 |
| `sentences-ko-themed-topik.json`   |              19 |
| `sentences-ko-themed.json`         |               1 |
| `sentences-ko-study.json`          |               2 |

## Notable Revisions

- Replaced awkward nominalized verb forms with natural adnominal or conjugated forms: `끄는 것이`, `드리는 것이`, `퍼요`, `넣어 두었어요`.
- Repaired sentences where the Korean no longer contained the intended target form, especially mined ROM entries whose target lemma/gloss had drifted.
- Normalized bad move templates:
  - `도감에 ... 적혀 있어요` -> `기술 목록에 ... 있어요`
  - `...는 매우 강한 기술이에요` -> `...은/는 포켓몬이 시합에서 쓰는 기술이에요`
  - `...가 들판에 울려 퍼졌어요` -> `포켓몬이 ...을/를 사용했어요`
  - `... 특성으로 유명해요` -> `... 특성을 가지고 있어요`
- Fixed TOPIK-style spacing/counters/collocations: `제5호`, `전화번호`, `일급`, `오천 엔`, `발견했어요`, `복사했어요`, `공짜로 들어갈 수 있어요`.
- Repaired Pokemon-specific lore/collocation issues for entries such as `레어코일`, `스라크`, `라이코`, and `애버라스`.

## Validation

- `jq empty` passes for all five edited JSON files.
- Invariant check passes: no blank generated entries, no English/editorial artifacts in `korean`, and no stale `targetForm` values among edited files.
- Residual suspicious-template scan passes for: `울려 퍼졌어요`, `매우 강한 기술`, `도감에 ... 적혀`, `특성으로 유명`, `포켓볼`, `첫 날`, `전화 번호`, `일 급`, `오 천`, `보다 미리`, `발견을 했`, `복사를 했`, `공짜로 들어가요`, `꼬리 불꽃`, `전기쥐 포켓몬`.
- `./gradlew test --no-daemon` passes.

## Residual Risk

Romanization fields were kept in sync for edited records, but the audit focus was Korean naturalness, target-form correctness, and Pokemon theming. A separate romanization-only polish pass would be reasonable if pronunciation display fidelity becomes a priority.
