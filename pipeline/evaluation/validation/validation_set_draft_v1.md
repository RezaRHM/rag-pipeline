# Validation set draft (3-document corpus) — PARKED before scale-up

24 questions, verified against the current RD98XS/HR652/HP7 corpus. Parked
because the system is being generalised to many more documents; questions will
need review once retrieval and routing are no longer tuned to three products.

## Factual (well-formed) — retrieval confirmed
F1  What is the output power of the HR652 in high, middle, and low settings?   [Specifications: 44/40/30 dBm]
F2  What items are included in the RD98XS packing list?                         [1. Packing List]
F3  Which connectors are on the rear panel of the RD98XS?                       [2.2 Rear Panel]
F4  Can alcohol be used to clean the HR652?                                     [9.2 Product Cleaning: no]
F5  What is on the front panel of the HR652?                                    [2. Product Layout; lexical_gap]

## Telegraphic (paired with F)
T1  HR652 output power?
T2  RD98XS box contents?                                                        [heading arm]
T3  RD98XS rear connectors?
T4  HR652 cleaning alcohol?

## Unsupported (3-layer verified)
U1  What is the RF output power of the RD98XS?          [absent; trap: low TX power / 100W PSU]
U2  What is the frequency range of the RD98XS?          [absent; trap: 6.6 VSWR antenna freq]
U3  What is the weight of the HR652?                     [mentioned, no figure]
U4  Is the RD98XS IP68 rated?                            [absent; trap: HP7 is IP68]

## Ambiguous (divergence-classified)
A1  Cleaning instructions?        [optional; both nearly identical]
A2  What's in the box?            [required; DC Power Cord vs Power Cord]
A3  Antenna connector type?       [required; RD98XS Type-N, HR652 unclear]
A4  Ground screw location?        [required; RD98XS rear panel, HR652 unclear]

## Multi-section
M1  = F5
M2  Before cleaning the RD98XS, what to do first and what to avoid?             [7.2]
M3  Steps to install the RD98XS and confirm it works afterward?                 [3.2.2 + 3.3]
M4  After installing the RD98XS, confirm power-on and what the LEDs mean?       [3.3 + 5.2]

## Comparison / use-case
C1  Do RD98XS and HR652 ship with the same accessories?                         [Packing List x2]
C2  Which repeater documents its output power?                                  [HR652 yes, RD98XS no]
C3  Which repeater needs a Phillips screwdriver, RD98XS or HR652?               [RD98XS 3.1 vs HR652 4.1 Tools]
C4  Compare the alarm code systems of the RD98XS and HR652.                     [RD98XS 6.x named vs HR652 E-codes]

## Known routing issue found while building this
"Do both repeaters use the same alarm codes?" (phrased with "same") routes to
needs_clarification because "alarm" is a clarification trigger keyword. Phrasing
with "compare"/"differ" routes correctly to comparison. The clarification gate
over-triggers on comparison questions that contain a topic keyword. Recorded for
the routing rework.
