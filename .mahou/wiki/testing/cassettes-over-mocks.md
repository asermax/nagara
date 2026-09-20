# Cassettes over mocks

The api suite replays a service behind an HTTP boundary, the extraction pipeline, from cassettes exactly as it replays firecrawl and gemini, so the client's real serialization and parsing run against the recorded shapes. Mocks are for calls that are not plain HTTP.

- Record against the real service when it can run: `wrangler dev` needs no account and serves on localhost. The conftest's matching rules carry the hard parts: body matching disambiguates POSTs to one URL, and repeated identical GETs replay in recorded order, which is a poll sequence.
- Fabricate when the service does not exist yet: a cassette is YAML of request and response pairs, hand-built from the boundary contract. The trade is that a recorded cassette is evidence the service answered, and a fabricated one is the contract restated as a fixture, so drift passes unnoticed. Both sides are ours, so the risk is small.
- The unreachable case cannot be a cassette: a refused connection produces no interaction. Point the client at 127.0.0.1, a closed port that refuses instantly, with recording disabled for that one test. The failure is a genuine network one.
- Mocks stay for what is not HTTP: modal's spawn-and-resolve, the gemini describer SDK.
- Volatile ids break replay: minted `itm_` handles differ per run. A registered matcher normalizes them on both sides, cassette and request, so one cassette replays across any mint.
