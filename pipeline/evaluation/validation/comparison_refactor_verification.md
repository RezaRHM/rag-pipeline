# Comparison refactor - verification report

Branch `comparison-pipeline-refactor` (cc07c88 + 96beda2 + b7c3ab5), generated 2026-07-17 with query_cache cleared, temperature=0.

For each case: the final pipeline answer, then EVERY chunk the comparison retrieval fed to the model, verbatim, per product.


---

## C1: Do RD98XS and HR652 ship with the same accessories?

**method:** freeform | **status:** compared

### Final answer

**HR652 Digital Repeater**

1. The HR652 ships with a Power Cord (1 PCS) ([1. Packing List])
2. The HR652 ships with a Documentation Kit (1 PCS) ([1. Packing List])

**RD98XS Digital Repeater**

1. The RD98XS ships with a DC Power Cord (1 PCS) ([1. Packing List])
2. The RD98XS ships with a Documentation Kit (1 PCS) ([1. Packing List])

Based on the facts, both repeaters ship with a Documentation Kit and a power cord, but they are different types of power cords: HR652 has a Power Cord, while RD98XS has a DC Power Cord. Therefore, it can be concluded that they do not ship with the same accessories.

### Retrieved evidence chunks (exactly what the model saw)


#### RD98XS Digital Repeater - 4 chunks


**[chunk 1] Section: RF Radiation Profile**

```
## RF Radiation Profile
Radio Frequency (RF) is a frequency of electromagnetic radiation in the range at which radio signals are transmitted. RF technology is widely used in communication, medicine, food processing and other fields. It may generate radiation during use.
```

**[chunk 2] Section: Key Operations**

```
## Key Operations
| Operation      | Description                             |
|----------------|-----------------------------------------|
| Short press    | Press and release quickly.              |
| Long press     | Press and hold for the preset duration. |
| Press and hold | Keep the key pressed.                   |
```

**[chunk 3] Section: 8. Optional Accessories**

```
## 8. Optional Accessories
<!-- image -->

Use the accessories specified by the Company only. If not, Hytera shall not be liable for any losses or damages arising out of use of unauthorized accessories.

For more information of the main optional accessories for the repeater, please consult your local dealer.

<!-- image -->

Existing devices should be upgraded to Hytera ' s iM or iS before being used as part of a system. Spea k to your Hytera dealer about how to upgrade your existing devices and for more information on Hytera ' s iM or iS firmware.

<!-- image -->

2018 Hytera Communications Corporation Limited. Hytera Communications Corporation Limited.

Address: Hytera Tower,Hi-Tech Industrial Park North,9108#Beihuan Road, Nanshan District,Shenzhen,People's Republic of China
```

**[chunk 4] Section: 1. Packing List**

```
## 1. Packing List
Please unpack carefully and check that you have received the following items. If any item is missing or damaged, please contact your dealer.

| Item          |   Quantity (PCS) | Item              | Quantity (PCS)   |
|---------------|------------------|-------------------|------------------|
| Repeater      |                1 | Documentation Kit | 1                |
| DC Power Cord |                1 | /                 | /                |

<!-- image -->

-  Figures in this manual are for reference only.
-  Check the main unit label to ensure that the purchased product is correct.
```

#### HR652 Digital Repeater - 3 chunks


**[chunk 1] Section: 10. Optional Accessories**

```
## 10. Optional Accessories
Use the accessories specified by the Company only. Otherwise, we will not be liable for any loss or damage arising out of use of unauthorized accessories.

Contact your dealer for the optional accessories used with the product.
```

**[chunk 2] Section: 2. Product Layout**

```
## 2. Product Layout
<!-- image -->

|   No. | Part Name                                  |   No. | Part Name               |
|-------|--------------------------------------------|-------|-------------------------|
|     1 | Bottom cover                               |    12 | Analog mode indicator   |
|     2 | USB port                                   |    13 | Timeslot A TX indicator |
|     3 | TX/Duplexer antenna connector (UHF female) |    14 | Timeslot A RX indicator |
|     4 | Accessory connector                        |    15 | Timeslot B TX indicator |
|     5 | Ethernet port                              |    16 | Timeslot B RX indicator |
|     6 | Power inlet                                |    17 | Alarm indicator         |
|     7 | RX antenna connector (SMA female)          |    18 | Fan                     |
|     8 | GNSS antenna connector (SMA female)        |    19 | Volume/Channel up key   |
|     9 | Aviation port                              |    20 | Seven-segment LED       |
|    10 | On-Off key                                 |    21 | Volume/Channel down key |
|    11 | Digital mode indicator                     |    22 | Battery latch           |

<!-- image -->

Except that the low-power HR652 features no fan but the high-power HR65X features one, the other hardware of the two types is the same.
```

**[chunk 3] Section: 1. Packing List**

```
## 1. Packing List
Unpack carefully and check that you have received the following items. If any item is missing or damaged, contact your dealer.

| Item       |   Quantity (PCS) | Item              | Quantity (PCS)   |
|------------|------------------|-------------------|------------------|
| Repeater   |                1 | Documentation Kit | 1                |
| Power Cord |                1 | /                 | /                |

<!-- image -->

Figures in this document are for reference only.
```

---

## C3: Which repeater needs a Phillips screwdriver, RD98XS or HR652?

**method:** structured | **status:** compared

### Final answer

**Answer:** Both products document the compared items; the exact documented values are shown side by side below.

| Compared item | HR652 Digital Repeater | RD98XS Digital Repeater |
|---|---|---|
| required tool | Phillips screwdriver (4.2 Procedure → Remove the decorative cover.) | Phillips screwdriver (3.1 Installation Requirements) |

*Every value is quoted from that product's own manual; sections in parentheses.*

### Retrieved evidence chunks (exactly what the model saw)


#### RD98XS Digital Repeater - 3 chunks


**[chunk 1] Section: 3.1 Installation Requirements**

```
## 3.1 Installation Requirements
Ensure the following requirements are met:

-  Environment:  a  dry  and  well-ventilated  place  with  ambient  temperature  of  -30°C  to  +60°C  and relative humidity of 95%
-  Location: in a rack, bracket, or cabinet, or on a desk
-  Tools: a Phillips screwdriver, a T-10 torx screwdriver, and a spanner
-  Voltage of DC power: 13.6±15% V

<!-- image -->

Refer to the Safety Information Booklet for more information.
```

**[chunk 2] Section: FCC Statement**

```
## FCC Statement
This equipment has been tested and found to comply with the limits for a Class B digital device, pursuant to  part  15  of  FCC  Rules. These limits are designed to provide reasonable protection against harmful interference  in  a  residential  installation.  This  equipment  generates  and  can  radiate  radio  frequency energy. If not installed and used in accordance with the instructions, it may cause harmful interference to radio  communications. However, there is no guarantee that interference will not occur in a particular installation. Verification of harmful interference by this equipment to radio or television reception can be determined by turning it off and then on. The user is encouraged to try to correct the interference by one or more of the following measures:

-  Reorient or relocate the receiving antenna. Increase the separation between the equipment and receiver.
-  Connect the equipment into an outlet on a different circuit to that of the receiver's outlet.
-  Consult the dealer or an experienced radio/TV technician for help.

Operation is subject to the following two conditions:

-  This device may not cause harmful interference.
-  This device must accept any interference received, including interference that may cause undesired operation.

Note:  Changes  or  modifications  to  this  unit  not  expressly  approved  by  the  party  responsible  for compliance could void the user's authority to operate the equipment.
```

**[chunk 3] Section: 3.2.1 Installing the Duplexer (Optional)**

```
## 3.2.1 Installing the Duplexer (Optional)
If  the  repeater  works  with  a  duplexer,  install  the  duplexer  into  the  repeater  according  to  the  following diagrams and steps before installing the repeater.

Duplexer with front side facing upwards

<!-- image -->

RF Cable

Assembly Screws

Assembly Screws RF Cable

Assembly Screws

Duplexer with front side facing downwards

<!-- image -->

1.    Loosen the three screws on the bracket with a Phillips screwdriver.

<!-- image -->

Power Cord

© NOTE

Chaomi

Data Cable RF Cable

2

2.    Install the duplexer onto the bracket.

<!-- image -->

LOW

Observe the specifications  of  the  two  antenna  interfaces  on  the  duplexer  to  determine  which  one should be connected to the repeater. The interface connecting the repeater should be close to PA module to reduce RF loss.

<!-- image -->

3.    Loosen the screws at the back of the repeater top cover, and then pull the top cover backwards to remove it.
4.    Loosen the six screws locking the PA module of the repeater, remove all power, data and RF cables from the PA, and then remove the PA module.

<!-- image -->

<!-- image -->

© NOTE

Vanil

5.    Connect the RF cable through the hole next to the PA module.
6.    Install the duplexer to the repeater.

<!-- image -->

Mount the duplexer on the exciter module and receiver module of the repeater, and then fasten the duplexer with the two screws inside the housing and the two screws on the side of the housing.

7.    Attach the PA module and connect all PA power, data and RF cables to it.
8.    Close the repeater cover.

The installation is complete.
```

#### HR652 Digital Repeater - 4 chunks


**[chunk 1] Section: 4.1 Tools**

```
## 4.1 Tools
-  Electric drill
-  Screwdriver
-  Wrench
-  Anti-static gloves
```

**[chunk 2] Section: FCC Statement**

```
## FCC Statement
This equipment has been tested and found to comply with the limits for a Class B digital device, pursuant to part 15 of  FCC  Rules.  These  limits  are  designed  to  provide  reasonable  protection  against  harmful  interference  in  a residential installation. This equipment generates and can radiate radio frequency energy. If not installed and used in accordance with the instructions, it may cause harmful interference to radio communications. However, there is no guarantee that interference will not occur in a particular installation. Verification of harmful interference by this equipment to radio or television reception can be determined by turning it off and then on. The user is encouraged to try to correct the interference by one or more of the following measures:

-  Reorient or relocate the receiving antenna. Increase the separation between the equipment and receiver.
-  Connect the equipment into an outlet on a different circuit to that of the receiver's outlet.
-  Consult the dealer or an experienced radio/TV technician for help.

Operation is subject to the following two conditions:

-  This device may not cause harmful interference.
-  This device must accept any interference received, including interference that may cause undesired operation.

Note: Any changes or modifications to this unit not expressly approved by the party responsible for compliance could void the user's authority to operate the equipment.
```

**[chunk 3] Section: 7.5.2 Solution**

```
## 7.5.2 Solution
When the repeater triggers this alarm, to avoid risk of burns, DO NOT touch the repeater.

- Use the digital thermometer with thermocouple to check whether the surface temperature of the PA module is over 90°C.
-  If yes, go to step 2.
-  If no, go to step 3.
- Check  whether  the  ambient  temperature  and  ventilation  conditions  of  the  repeater  meet  the  installation requirements.

<!-- image -->

For the high-power HR652 , besides the temperature and ventilation conditions, check whether the fan works and the heat exhaust duct is clean.

-  If yes, go to step 3.
-  If no, take appropriate measures (for example, install more heat sink devices, replace fans, or clean the duct) to reduce the ambient temperature and improve ventilation.
- Check whether the TX power is too high and the temperature of heat sink is rising too fast.
-  If yes, go to step 4.
-  If no, contact your local dealer for technical support.
- Check whether the RF adapter cable, antenna, or feed line is properly connected.
-  If yes, contact your dealer for technical support.

-  If no, re-connect or replace the cable, antenna, or feed line.
```

**[chunk 4] Section: 4.2 Procedure → Remove the decorative cover.**

```
## 4.2 Procedure → Remove the decorative cover.
- a. Use the torx screwdriver to remove the three screws fixing the bottom decorative cover, and then remove the bottom decorative cover.
- b. Use the torx screwdriver to remove the two screws fixing the left decorative cover.
- c. Push  the  left  decorative  cover  downwards ① ,  and  then  remove  the  left  decorative  cover ② and  the waterproof cover for USB port.

3

Bottom cover

4.

Left decorative cover

Waterproof cover for

USB port

- d. Use the torx screwdriver to remove the two screws fixing the right decorative cover.
- e. Push the right decorative cover downwards ③ , and then remove the left decorative cover ④ , battery latch, and spring. 3

Fixing screw for decorative cover

3. Remove the rear housing.

<!-- image -->

- Remove the rear housing.
- a. Use the Phillips screwdriver to remove the pan head screw.
- b. Use the torx screwdriver to remove the torx screw.
- c. Remove the rear housing.
- Install the duplexer.
- a. Align the mounting holes on the duplexer with the screw holes on the mounting bracket of the repeater.

<!-- image -->

Fixing screw (pan head, M 2.5) for housing

9:58280

Front housing

Right decorative cover

1.

Pan head screw (M2.5 x 5)

RF cable 1

Duplexer

Mounting bracket

- b. Secure the duplexer to the mounting bracket with pan head screws (M 2.5 x 5).

0

<!-- image -->

- Connect the RF cable.

<!-- image -->
```

---

## C4: Compare the alarm code systems of the RD98XS and HR652.

**method:** freeform | **status:** compared

### Final answer

**HR652 Digital Repeater**

1. The alarm codes are listed in [6.2 Seven-Segment LED → Alarm Code].
2. The alarm codes include:
	* E1: Battery unmatched alarm
	* E2: Low battery alarm
	* E3: External power under-voltage alarm
	* E4: TX unlocked alarm
	* E5: RX unlocked alarm
	* E6: Over-temperature alarm
	* E7: Voltage standing wave ratio (VSWR) alarm
	* E8: Off-lease alarm
	* E9: Secondary repeater unregistered alarm
	* EE: Repeater disabled alarm
	* Eb: Low forward power alarm
	* EH: External power over-voltage alarm
	* H3: Network IP conflict alarm
	* H5: Invalid network IP alarm
	* bP: Backup alarm

**RD98XS Digital Repeater**

1. The alarm codes are not explicitly listed in the provided excerpts, but the [6.2 TX/RX Unlock Alarm → Solution] section mentions a "TX/RX Unlock" alarm.
2. The [5.1 Checking LCD Indications] section lists icons for various conditions, including:
	* Low TX power
	* High TX power
	* An accessory is connected
	* An alarm message is given
	* GPS signals do not synchronize with satellite signals
	* GPS signals synchronize with satellite signals
	* Repeater Mode (RM)
	* Monitor feature enabled
	* Scrambler/Encrypt feature enabled
	* Scan in progress
	* Speaker unmuted
	* Repeater connected to the network
	* Repeater disconnected from the network
	* Network cable removed

**Comparison**

The HR652 has a more extensive list of alarm codes, including specific conditions such as battery unmatched and off-lease alarms. The RD98XS does not have an explicit list of alarm codes but mentions a "TX/RX Unlock" alarm in one section. The RD98XS also has icons for various conditions, but these are not directly comparable to the alarm codes on the HR652.

Therefore, based on the provided excerpts, it appears that the HR652 has a more comprehensive and detailed alarm code system compared to the RD98XS.

### Retrieved evidence chunks (exactly what the model saw)


#### RD98XS Digital Repeater - 4 chunks


**[chunk 1] Section: 6.3 Fan Failure Alarm → Description**

```
## 6.3 Fan Failure Alarm → Description
When the repeater is operating at high temperature and the fan fails to work, the Alarm Indicator glows red and the LCD displays the message below:

!

!

Over

Temperature!

• Fan Locked!

<!-- image -->

Then the repeater will automatically work at low TX power to avoid overheating.
```

**[chunk 2] Section: 6. Alarm Information**

```
## 6. Alarm Information
With the Alarm feature enabled by your dealer, the repeater can detect alarms. When an error occurs, the LCD displays the alarm message with the Alarm Indicator on the front panel glowing red.
```

**[chunk 3] Section: 5.1 Checking LCD Indications**

```
## 5.1 Checking LCD Indications
<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

| Icon   | Description                                                                              |
|--------|------------------------------------------------------------------------------------------|
|        | Low TX power for the current channel.                                                    |
|        | High TX power for the current channel.                                                   |
|        | An accessory is connected.                                                               |
|        | An alarm message is given.                                                               |
|        | The GPS signals do not synchronize with the satellite signals.                           |
|        | The GPS signals synchronize with the satellite signals.                                  |
| RM     | Repeater Mode: The repeater forwards the communication requests from radios and systems. |
|        | The Monitor feature is enabled.                                                          |
|        | The Scrambler/Encrypt feature is enabled.                                                |
|        | Scan is in progress.                                                                     |
|        | The speaker is unmuted.                                                                  |
|        | The repeater is connected to the network.                                                |
|        | The repeater is disconnected from the network.                                           |
|        | The network cable is removed from the repeater.                                          |
```

**[chunk 4] Section: 6.2 TX/RX Unlock Alarm → Solution**

```
## 6.2 TX/RX Unlock Alarm → Solution
Disconnect the power supply, and then open the chassis to check if any cable is loose or damaged.

-  If yes, secure or replace the cable.
-  If no, contact your local dealer for technical support.

After the TX/RX Unlock recovers the normal operation, the message disappears, and the Alarm Indicator goes off.
```

#### HR652 Digital Repeater - 2 chunks


**[chunk 1] Section: 6.2 Seven-Segment LED → Alarm Code**

```
## 6.2 Seven-Segment LED → Alarm Code
| Alarm Code   | Description                              | Alarm Code   | Description                           |
|--------------|------------------------------------------|--------------|---------------------------------------|
| E1           | Battery unmatched alarm                  | E9           | Secondary repeater unregistered alarm |
| E2           | Low battery alarm                        | EE           | Repeater disabled alarm               |
| E3           | External power under-voltage alarm       | Eb           | Low forward power alarm               |
| E4           | TX unlocked alarm                        | EH           | External power over-voltage alarm     |
| E5           | RX unlocked alarm                        | H3           | Network IP conflict alarm             |
| E6           | Over-temperature alarm                   | H5           | Invalid network IP alarm              |
| E7           | Voltage standing wave ratio (VSWR) alarm | bP           | Backup alarm                          |
| E8           | Off-lease alarm                          | /            | /                                     |
```

**[chunk 2] Section: 2. Product Layout**

```
## 2. Product Layout
<!-- image -->

|   No. | Part Name                                  |   No. | Part Name               |
|-------|--------------------------------------------|-------|-------------------------|
|     1 | Bottom cover                               |    12 | Analog mode indicator   |
|     2 | USB port                                   |    13 | Timeslot A TX indicator |
|     3 | TX/Duplexer antenna connector (UHF female) |    14 | Timeslot A RX indicator |
|     4 | Accessory connector                        |    15 | Timeslot B TX indicator |
|     5 | Ethernet port                              |    16 | Timeslot B RX indicator |
|     6 | Power inlet                                |    17 | Alarm indicator         |
|     7 | RX antenna connector (SMA female)          |    18 | Fan                     |
|     8 | GNSS antenna connector (SMA female)        |    19 | Volume/Channel up key   |
|     9 | Aviation port                              |    20 | Seven-segment LED       |
|    10 | On-Off key                                 |    21 | Volume/Channel down key |
|    11 | Digital mode indicator                     |    22 | Battery latch           |

<!-- image -->

Except that the low-power HR652 features no fan but the high-power HR65X features one, the other hardware of the two types is the same.
```