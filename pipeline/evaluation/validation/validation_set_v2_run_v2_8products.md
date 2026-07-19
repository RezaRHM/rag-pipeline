# Validation set v2 (8-product corpus) — run: v2_8products

Completed: 20/20

## N1 — factual

**Question:** What tools are needed to install the RD625?

**Expected:** An electric drill and a T10 torx screwdriver

**Intent:** `procedural` — **Route:** `ready` — **Product:** `RD625 Digital Repeater` — **Time:** `25.7s`

**Retrieved sections:**

- Installation Tools
- A.  Install the wall-mount bracket.
- Wall-mount Bracket Installation (Optional)
- Operation Environment
- B.  Install the repeater on the bracket.

**Answer:**

According to the documentation, the tools needed to install the RD625 Digital Repeater are an electric drill and a T10 torx screwdriver. 

[Source: RD625 Digital Repeater — Installation Tools]

---

## N2 — factual

**Question:** What is the operating voltage of the RD625?

**Expected:** DC 13.6V +/-15%; AC 90V to 264V

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD625 Digital Repeater` — **Time:** `15.6s`

**Retrieved sections:**

- Voltage Check
- Operation Environment
- Product Check
- Installation Tools
- Instructions

**Answer:**

The operating voltage of the RD625 is 13.6V ± 15% for DC power supply (Source: RD625 Digital Repeater — Voltage Check). 

Additionally, for AC power supply, it can operate within a range of 90V to 264V (Source: RD625 Digital Repeater — Voltage Check).

---

## N3 — factual

**Question:** What happens on the RD962i when the battery is low?

**Expected:** Below 12% threshold: alarm indicator red, LED segment shows E2

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD962i Digital Repeater` — **Time:** `21.3s`

**Retrieved sections:**

- Low Battery
- Battery Mismatch
- LED Segment Display Indication
- Powering on/off manually

**Answer:**

When the battery is low (below 12% of its capacity), the alarm indicator will glow red and the LED segment display will show 'E2'. The repeater will still work properly but will power off automatically when running out of power. 

[Source: RD962i Digital Repeater — Low Battery]

---

## N4 — factual

**Question:** What ingress protection rating does the RD965 have?

**Expected:** IP67, and MIL-STD-810 C/D/E/F/G

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD965 Digital Repeater` — **Time:** `24.7s`

**Retrieved sections:**

- Outdoor operation and IP67 degree of protection
- RD965
- 16 channels → Technical Data
- Small backup battery (optional)
- Flexible networking

**Answer:**

According to the provided context, the RD965 has an IP67 degree of protection (Source: RD965 Digital Repeater — Outdoor operation and IP67 degree of protection).

---

## N5 — factual

**Question:** What is the capacity of the optional RD965 backup battery?

**Expected:** 10 Ah lithium-ion, at least 8 hours at 50% duty cycle

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD965 Digital Repeater` — **Time:** `25.3s`

**Retrieved sections:**

- Small backup battery (optional)
- Slimline and portable
- 16 channels → Optional accessories
- 16 channels → Technical Data
- 16 channels → Flexible applications

**Answer:**

According to the provided context, the capacity of the optional RD965 backup battery is 10 Ah. 

[Source: RD965 Digital Repeater — Small backup battery (optional)]

---

## T1 — telegraphic

**Question:** RD625 installation tools?

**Expected:** Electric drill + T10 torx; intent should be standard

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD625 Digital Repeater` — **Time:** `19.1s`

**Retrieved sections:**

- Installation Tools
- A.  Install the wall-mount bracket.
- Wall-mount Bracket Installation (Optional)
- Operation Environment
- B.  Install the repeater on the bracket.

**Answer:**

According to the documentation, the installation tools for the RD625 Digital Repeater are an electric drill and a T10 torx screwdriver. 

[Source: RD625 Digital Repeater — Installation Tools]

---

## T2 — telegraphic

**Question:** RD965 GPS?

**Expected:** GPS module enables real-time location monitoring

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD965 Digital Repeater` — **Time:** `26.2s`

**Retrieved sections:**

- GPS
- RD965
- Slimline and portable
- Outdoor operation and IP67 degree of protection
- 16 channels → Technical Data

**Answer:**

There is no information about the RD965 having a built-in GPS module in any of the provided sources. The context only mentions the GPS module as part of the "RD965 Digital Repeater — GPS" source, but this appears to be a separate document or product that is not related to the RD965 repeater itself.

However, it does mention that the GPS module enables emergency control rooms to monitor the location of a small radio network in real-time if the repeater is being used as a mobile unit. But there's no information about the RD965 having a built-in GPS module or any GPS capabilities.

---

## U1 — unsupported

**Question:** What is the output power of the RD625?

**Expected:** Absent: the RD625 document covers installation only

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD625 Digital Repeater` — **Time:** `16.3s`

**Retrieved sections:**

- Voltage Check
- Operation Environment
- Installation Tools
- Product Check
- A.  Install the wall-mount bracket.

**Answer:**

The provided context does not mention the output power of the RD625 Digital Repeater. The information available pertains to voltage checks, operation environment, installation tools, product check, and wall-mount bracket installation, but it does not include specifications on output power.

---

## U2 — unsupported

**Question:** Is the RD962i IP68 rated?

**Expected:** Absent; must not borrow IP67/IP68 from RD965 or HP7

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD962i Digital Repeater` — **Time:** `22.1s`

**Retrieved sections:**

- Operation Environment
- Voltage Check
- Instructional Icons
- Troubleshooting
- EU Regulatory Conformance

**Answer:**

The documentation does not mention the IP rating of the RD962i repeater.

---

## U3 — unsupported

**Question:** What is the frequency range of the RD625?

**Expected:** Absent: no specifications section in the RD625 document

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD625 Digital Repeater` — **Time:** `18.1s`

**Retrieved sections:**

- Voltage Check
- Operation Environment
- Installation Tools
- A.  Install the wall-mount bracket.
- Product Check

**Answer:**

The context does not mention the frequency range of the RD625.

---

## C1 — comparison

**Question:** Compare the installation tools of the RD625 and the RD962i.

**Expected:** RD625: drill + T10 torx; RD962i: cross head + T10 torx

**Intent:** `comparison` — **Route:** `ready` — **Product:** `None` — **Time:** `65.9s`

**Retrieved sections:**


**Answer:**

**RD962i Digital Repeater**

1. Tools required for installing the portable repeater include a cross head screwdriver and a T10 torx screwdriver. [Installation Tools]
2. The repeater must be installed in a dry and well-ventilated place with ambient temperature of -30 ℃ -+60 ℃ and relative humidity of not more than 95%. [Operation Environment]

**RD625 Digital Repeater**

1. An electric drill and a T10 torx screwdriver are required for installation. [Installation Tools]
2. The wall-mount bracket requires three ST4X16 self-tapping screws to fasten it on the wall. [A. Install the wall-mount bracket.]

**Comparison:**
The RD962i and RD625 share one common tool, a T10 torx screwdriver, required for installation. However, the RD962i also requires a cross head screwdriver, which is not mentioned in the RD625 documentation.

---

## C2 — comparison

**Question:** Compare the ingress protection of the RD965 and the RD98XS.

**Expected:** RD965: IP67; RD98XS: not documented

**Intent:** `comparison` — **Route:** `ready` — **Product:** `None` — **Time:** `60.6s`

**Retrieved sections:**


**Answer:**

**RD965 Facts:**

1. The RD965 complies with the standards MILSTD-810 C/D/E/F/G [Outdoor operation and IP67 degree of protection].
2. It conforms to the IP67 degree of protection, ensuring exceptional performance in harsh conditions [Outdoor operation and IP67 degree of protection].

**RD98XS Facts:**

1. Not documented.

**Answer:** The RD965 has an ingress protection rating of IP67, while there is no information about the ingress protection of the RD98XS in the provided context.

---

## C3 — comparison

**Question:** Do the RD962i and HR652 use the same alarm code for low battery?

**Expected:** Yes - both use E2 for the low-battery alarm

**Intent:** `comparison` — **Route:** `ready` — **Product:** `None` — **Time:** `83.0s`

**Retrieved sections:**


**Answer:**

**HR652 Digital Repeater**

1. The HR652 has a Seven-Segment LED display that shows various alarm codes, including E2 for Low battery alarm [6.2 Seven-Segment LED → Alarm Code].
2. The HR652 has an optional battery accessory that can be purchased separately [7.2 Low Battery Alarm].
3. The HR652 has no fan, but it has a power inlet and a GNSS antenna connector (SMA female) [2. Product Layout].

**RD962i Digital Repeater**

1. The RD962i has a low-battery alarm that is triggered when the battery power falls below 12% of its capacity by default, displaying 'E2' on the LED segment display [Low Battery].
2. When powered by an external power supply, the repeater will automatically power on and eliminate the low-battery alarm.

**Answer**

No, the RD962i and HR652 do not use the same alarm code for low battery. The RD962i displays 'E2' for low battery, while the HR652 displays E2 as part of its Seven-Segment LED display, but it is not explicitly stated that this corresponds to a specific alarm code in the HR652 documentation.

---

## C4 — comparison

**Question:** Compare the installation tools of the RD98XS and the RD625.

**Expected:** RD98XS: Phillips + T-10 torx + spanner; RD625: drill + T10 torx

**Intent:** `comparison` — **Route:** `ready` — **Product:** `None` — **Time:** `82.4s`

**Retrieved sections:**


**Answer:**

**RD625 Digital Repeater**

1. An electric drill [Installation Tools]
2. A T10 torx screwdriver [Installation Tools]
3. ST4X16 self-tapping screws [A. Install the wall-mount bracket.]

**RD98XS Digital Repeater**

1. A Phillips screwdriver [3.1 Installation Requirements]
2. A T-10 torx screwdriver [3.1 Installation Requirements]
3. A spanner [3.1 Installation Requirements]

Based on the facts listed above, the installation tools for the RD625 and RD98XS differ in that:

* The RD625 requires an electric drill, while the RD98XS does not mention a drill as a required tool.
* Both repeaters require a T10 torx screwdriver, but the RD625 also mentions it under [Installation Tools], whereas the RD98XS mentions it under [3.1 Installation Requirements].
* The RD625 uses ST4X16 self-tapping screws, while the RD98XS does not specify any specific type of screw.
* The RD98XS requires a spanner, which is not mentioned in the RD625 documentation.

Therefore, the installation tools for the two repeaters are not identical.

---

## C5 — comparison

**Question:** Which repeater documents a backup battery?

**Expected:** No products named in an eight-product corpus -> needs_clarification

**Intent:** `comparison` — **Route:** `needs_clarification` — **Product:** `None` — **Time:** `7.6s`

**Retrieved sections:**


**Answer:**

Please specify the two products you want to compare.

---

## A1 — ambiguous

**Question:** What installation tools do I need?

**Expected:** Clarification required: tools differ per product

**Intent:** `procedural` — **Route:** `needs_clarification` — **Product:** `None` — **Time:** `61.3s`

**Retrieved sections:**


**Answer:**

The answer depends on the product model — "required tool" differs between the documented models. Relevant documentation was found for: RD625 Digital Repeater, RD962i Digital Repeater, RD98XS Digital Repeater. Please specify which product you mean.

---

## A2 — ambiguous

**Question:** What is the operating voltage?

**Expected:** Clarification required: voltage differs per product

**Intent:** `standard` — **Route:** `needs_clarification` — **Product:** `None` — **Time:** `68.5s`

**Retrieved sections:**


**Answer:**

The answer depends on the product model — "operating voltage" differs between the documented models. Relevant documentation was found for: HR652 Digital Repeater, RD625 Digital Repeater, RD962i Digital Repeater, RD98XS Digital Repeater. Please specify which product you mean.

---

## A3 — ambiguous

**Question:** Is it waterproof?

**Expected:** Clarification required: only some products document IP ratings

**Intent:** `standard` — **Route:** `needs_clarification` — **Product:** `None` — **Time:** `42.7s`

**Retrieved sections:**


**Answer:**

This depends on the product model. Relevant documentation was found for: HP7 SERIES, HR106X Digital Repeater, RD962i Digital Repeater. Please specify which product you mean.

---

## M1 — procedural

**Question:** How do I install the RD625 on a wall, step by step?

**Expected:** Drill three holes, wall anchors, three ST4X16 self-tapping screws, then mount

**Intent:** `procedural` — **Route:** `ready` — **Product:** `RD625 Digital Repeater` — **Time:** `34.7s`

**Retrieved sections:**

- A.  Install the wall-mount bracket.
- B.  Install the repeater on the bracket.
- Installation Tools
- Wall-mount Bracket Installation (Optional)
- Operation Environment

**Answer:**

To install the RD625 Digital Repeater on a wall, follow these steps:

1. **Drill three holes into the wall**: Align each hole with those of the wall-mount bracket.
2. **Put the plastic wall anchor into the drilled holes** (if the wall is concrete). Skip this step if the wall is not concrete.
3. **Use three ST4X16 self-tapping screws to fasten the bracket on the wall**.

Note: Ensure the wall can support the repeater's weight before drilling.

After installing the wall-mount bracket, follow these steps:

1. **Align the screws on the upper side of the repeater with the notches of the bracket**.
2. **Mount the repeater onto the bracket**, as shown in the figure below.
3. **Move the repeater side to side slightly to ensure the screws fit into the bottom of the notch**.

Make sure you have the required tools: an electric drill and a T10 torx screwdriver.

Note that installing the wall-mount bracket is optional, but if you need one, contact your dealer to purchase it.

---

## M2 — procedural

**Question:** How is the transmit power level set on the RD962i?

**Expected:** Dealer sets Tx power to High or Low

**Intent:** `standard` — **Route:** `ready` — **Product:** `RD962i Digital Repeater` — **Time:** `34.7s`

**Retrieved sections:**

- Adjusting the Power Level
- Voltage Check
- Low Battery
- Powering on/off manually
- Auto Power On

**Answer:**

According to the documentation, you can request your dealer to set the Tx power to High or Low. (Source: RD962i Digital Repeater — Adjusting the Power Level)

---
