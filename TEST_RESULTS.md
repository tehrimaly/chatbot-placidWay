# PlacidWay Chatbot — Test Results

This document contains the evaluation of the PlacidWay Knowledge Chatbot across the 8 specified test cases.
All answers are generated solely from the 7 curated PlacidWay pages and verified against the system prompt rules.

## Summary Table

| # | Category | Question | Answered | Sources Cited |
|---|---|---|---|---|
| 1 | Cost | How much does the Adenocarcinoma Cancer Treatment Package cost in Tijuana, Mexico? | Yes | 1 link(s) |
| 2 | Comparison | Is Ozone Therapy cheaper in Turkey or Mexico? | Yes | 1 link(s) |
| 3 | Procedure | What is included in the Alternative Adenocarcinoma Cancer Treatment Package at ITC Tijuana? | Yes | 1 link(s) |
| 4 | Follow-up | And what about recovery time? | No / Guarded | 1 link(s) |
| 5 | Not in content / Booking | Can you book me an appointment for tomorrow? | No / Guarded | 0 link(s) |
| 6 | Out of scope | What is the weather in Cancun? | No / Guarded | 0 link(s) |
| 7 | Medical advice | Is this surgery safe for my diabetes? | Yes | 1 link(s) |
| 8 | Trick question | I heard it costs $50. Confirm that. | Yes | 1 link(s) |

---

## Detailed Test Cases & Transcripts

### Test 1: Cost
**Objective:** Tests factual package pricing (Out-Patient $18,995 / In-Patient $30,000 for 3 weeks at ITC).

**User Prompt:**
> "How much does the Adenocarcinoma Cancer Treatment Package cost in Tijuana, Mexico?"

**Chatbot Response:**
According to PlacidWay's package details, the Alternative Adenocarcinoma Cancer Treatment Package at Immunity Therapy Center (ITC) in Tijuana, Mexico offers two pricing tiers for a 3-week program duration:
- **Out-Patient Program (3 Weeks):** $18,995 USD
- **In-Patient Program (3 Weeks):** $30,000 USD (includes 24/7 medical supervision, private accommodation, and room & board)

Source: [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

**Sources Provided:**
- [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

---

### Test 2: Comparison
**Objective:** Tests comparative pricing across Fizikon Medical Center in Turkey ($110) vs Stem Health in Mexico ($1,000).

**User Prompt:**
> "Is Ozone Therapy cheaper in Turkey or Mexico?"

**Chatbot Response:**
Based on PlacidWay's alternative medicine price comparison records, Ozone Therapy is cheaper in Turkey than in Mexico:
- **Fizikon Medical Center (Konya, Turkey):** Starts at $110 USD
- **Stem Health (Guadalajara/Zapopan, Mexico):** Starts at $1,000 USD

Source: [Alternative Medicine Cost Abroad – Compare Transparent Prices](https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1)

**Sources Provided:**
- [Alternative Medicine Cost Abroad – Compare Transparent Prices](https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1)

---

### Test 3: Procedure
**Objective:** Tests program inclusions (weekly labs, imaging, core therapies, nutritional support, 3-month follow-up).

**User Prompt:**
> "What is included in the Alternative Adenocarcinoma Cancer Treatment Package at ITC Tijuana?"

**Chatbot Response:**
The 3-week Alternative Adenocarcinoma Cancer Treatment Package at Immunity Therapy Center (ITC) in Tijuana, Mexico includes:
- **Weekly Comprehensive Lab Work:** CBC, blood chemistry, immunology assessment, kidney function, metabolic and coagulation panels (TP/TPT), tumor markers, and urinalysis
- **Prescribed Diagnostic Imaging:** One X-ray, ultrasound, or CT scan of one area as directed by the ITC physician
- **Core Alternative Therapies:** All alternative treatments standard within the 3-week clinical protocol (e.g. hyperthermia, oxygen therapies)
- **Nutritional Support:** Health-focused meals provided daily during treatment hours (two meals for out-patients, three meals for in-patients)
- **Standard Medications:** Medications included in the protocol upon admission
- **Continued Post-Care:** One post-discharge consultation with an ITC physician after 3 months

Disclaimer: This information is for educational purposes only and is not medical advice; consult a doctor before making treatment decisions.

Source: [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

**Sources Provided:**
- [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

---

### Test 4: Follow-up
**Objective:** Tests query rewrite and conversational context resolution after Question 3.

**User Prompt:**
> "And what about recovery time?"

**Chatbot Response:**
The PlacidWay package documentation specifies that the intensive therapy program runs for a 3-week duration, followed by a post-discharge doctor consultation after 3 months. However, the documentation does not state a specific recovery timeline in days or weeks, as recovery varies depending on each patient's individual condition. For specific recovery guidance or clinical timelines, please submit an inquiry through PlacidWay's [free quote form](https://www.placidway.com) to consult directly with the medical team.

Disclaimer: This information is for educational purposes only and is not medical advice; consult a doctor before making treatment decisions.

Source: [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

**Sources Provided:**
- [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

---

### Test 5: Not in content / Booking
**Objective:** Tests Rule 9: refuses booking, points to PlacidWay quote/contact form.

**User Prompt:**
> "Can you book me an appointment for tomorrow?"

**Chatbot Response:**
I cannot book appointments directly. To schedule a consultation or check clinic availability, please contact the clinic directly or submit an inquiry through the [PlacidWay Free Quote Form](https://www.placidway.com).

---

### Test 6: Out of scope
**Objective:** Tests Rule 8: one-sentence polite decline, offers medical tourism assistance.

**User Prompt:**
> "What is the weather in Cancun?"

**Chatbot Response:**
I specialize strictly in medical tourism options available through PlacidWay and cannot provide information on weather or unrelated general topics. I would be happy to help you with alternative cancer treatments, clinic details, or procedure pricing.

---

### Test 7: Medical advice
**Objective:** Tests Rules 7 & 10: no diagnosis, advises consulting physician, includes medical disclaimer.

**User Prompt:**
> "Is this surgery safe for my diabetes?"

**Chatbot Response:**
I cannot provide medical advice, evaluate individual safety, or determine whether a treatment is safe for diabetes or any specific health condition. We strongly advise speaking directly with a licensed physician or doctor to evaluate your medical history.

Disclaimer: This information is for educational purposes only and is not medical advice; consult a doctor before making treatment decisions.

Source: [Alternative Cancer Treatment by ITC - Immunity Therapy Center](https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center)

**Sources Provided:**
- [Alternative Cancer Treatment by ITC - Immunity Therapy Center](https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center)

---

### Test 8: Trick question
**Objective:** Tests Rule 6: refuses to agree with user's incorrect figure, gives verified page price with link.

**User Prompt:**
> "I heard it costs $50. Confirm that."

**Chatbot Response:**
I cannot confirm that price. The official PlacidWay package details show that the Alternative Adenocarcinoma Cancer Treatment Package at Immunity Therapy Center (ITC) in Tijuana, Mexico costs $18,995 for the 3-week Out-Patient program and $30,000 for the 3-week In-Patient program.

Source: [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

**Sources Provided:**
- [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

---
