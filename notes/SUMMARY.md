# SUMMARY

*Last updated 2026-07-23.*

The question is whether picking a GEPA reflection minibatch by SI-novelty actually improves
optimization, or whether the novelty signal we screened is just a correlate that falls apart once
you select on it. The test is 24 live HoVer runs: three arms (novelty-selected, cost-matched random,
plain baseline) across 8 paired seeds, with one confirmatory contrast.

The design is frozen and tagged at v2.1. The amendment that matters is the endpoint: it used to be a
val-argmax over 10 validation claims, and we found that lattice was so coarse that a tie-break
decided the winner on half the Stage-1 seeds. The endpoint is now an argmax over a fresh 50-claim
selection split. That fix is most of why the projected cost went from roughly $70 to roughly $190.

Everything is built and verified at zero spend — the runner, the supervisor, the wave manifest, and
every gated script, each of which refuses to run without an approval file that only Neel creates.
Nothing has been launched. The next move is Neel deciding which gates to open, starting with the
$3.13 grading pass that builds both held-out splits.
