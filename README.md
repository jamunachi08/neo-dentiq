# Neo Dentiq

Dental practice management built natively on Frappe and ERPNext.

Neo Dentiq runs the whole clinic: the diary, the clinical record, the odontogram, the
periodontal chart, sterilisation traceability, the lab bench, the implant registry and the
dental revenue cycle. Accounting, stock, purchasing, assets and HR are **not**
reimplemented — Neo Dentiq writes into ERPNext's own Sales Invoice, Payment Entry, Stock
Entry, Item, Batch, Serial No, Material Request, Purchase Invoice, Asset and Employee
documents. A dental group gets a real ERP underneath the clinic, not a silo beside it.

---

## Install

```bash
bench get-app neo_dentiq /path/to/neo_dentiq
bench --site your-site.local install-app neo_dentiq
bench --site your-site.local migrate
```

ERPNext is a hard requirement (`required_apps = ["frappe/erpnext"]`).

Installation seeds every master record automatically. Then:

1. Open **Neo Dentiq Settings**, set the default Company, Clinic and Price List.
2. Click **Install demo clinic** to create starter operatories, a weekday schedule, an
   autoclave and three instrument trays per kit.
3. Create your **Dental Practitioner** records and link each to an ERPNext Employee and a
   User.

---

## Modules

| Module | Purpose |
|---|---|
| **Neo Dentiq Masters** | Clinics, operatories, practitioners, procedures, codes, teeth, drugs, kits, payers, labs, templates |
| **Neo Dentiq Clinical** | Patient, odontogram, perio chart, SOAP notes, treatment plans, procedures, prescriptions, imaging, lab cases, implants, ortho |
| **Neo Dentiq Practice** | Appointments, waitlist, recalls, communications, referrals, practitioner leave |
| **Neo Dentiq Revenue Cycle** | Pre-authorisation, claims, remittance, payment plans |
| **Neo Dentiq Compliance** | Sterilisation cycles, instrument trays, biological indicators, infection control, incidents, equipment |

88 DocTypes, 1,508 fields. Five workspaces, nine query reports, nine dashboard charts,
three workflows, fourteen scheduled jobs.

---

## Master data shipped with the app

Everything below installs on `after_install` and is re-checked on every `migrate`. The
installer is additive and idempotent — it never overwrites a record you have edited.

| Master | Records | Notes |
|---|---|---|
| Tooth Master | 52 | 32 permanent + 20 primary, with FDI / Universal / Palmer notation, arch, quadrant, type, side, typical root and canal counts, valid surfaces |
| Tooth Surface | 10 | M, D, O, I, B, F, L, P, C, R |
| Dental Procedure Code | 62 | CDT (ADA) codes across diagnostic, preventive, restorative, endo, perio, prostho, surgery, implant, ortho, cosmetic and adjunctive |
| Dental Diagnosis Code | 27 | ICD-10-CM codes relevant to dentistry |
| Dental Procedure Category | 13 | Tree, each mapped to an ERPNext Item Group and a default treatment phase |
| Dental Procedure | 41 | Each auto-creates a non-stock ERPNext Item plus an Item Price, with chair time, consent/lab/radiograph flags, consumable bill of materials, instrument kit and clinical warranty |
| Clinical Pathway | 5 | Sequenced protocols: root canal, crown, single implant, perio steps 1–3, third molar |
| Medication Master | 31 | Dental formulary plus the systemic drugs needed for interaction checking |
| Drug Interaction Rule | 14 | Clinically significant pairs with severity, effect and management |
| Allergy Master | 14 | Drug, material, anaesthetic and food allergies with criticality flags |
| Medical Alert Master | 29 | Each with dental implications, chairside precautions, and flags for prophylaxis, bleeding risk, vasoconstrictor and NSAID avoidance, and medical clearance |
| Instrument Kit | 10 | Spaulding sterilisation class, required cycle type, instrument contents |
| Consumables and materials | 27 | ERPNext Items with batch/expiry tracking; implants also serial-tracked for UDI |
| Appointment Type | 15 | Duration, colour, online-bookable, required operatory type, intake form |
| Cancellation Reason | 14 | No-show, chargeable and waitlist-release behaviour |
| Recall Type | 7 | Risk-banded intervals: low / moderate / high |
| Referral Source | 10 | For acquisition-ROI reporting |
| Lab Case Type | 11 | Turnaround, cost and required stages |
| Consent Form Template | 8 | Full consent body, risks and alternatives: general, extraction, implant, endo, ortho, sedation, whitening, photography |
| Patient Intake Template | 1 (18 questions) | Answers map onto allergies, medical alerts, smoking status, pregnancy and caries risk |
| Radiograph Type | 9 | Effective dose in mSv for cumulative patient dose tracking |
| Dental Speciality | 12 | |
| Roles | 7 | Neo Dentiq Manager, Dentist, Dental Hygienist, Front Desk, Insurance Coordinator, Sterilization Officer, Patient Portal User |
| Workflows | 3 | Treatment Plan approval, Lab Case flow, Insurance Claim flow |
| Custom Fields | 14 | On Sales Invoice, Sales Invoice Item, Stock Entry, Customer, Item, Purchase Invoice, Employee |

---

## The processes

### 1. Registration and intake

```
Patient created ──► ERPNext Customer created automatically
        │
        ├──► Dental Chart seeded with the correct dentition (primary under age 6)
        └──► First Recall Schedule created at the default interval
```

Booking an appointment whose type requires an intake form creates a **Patient Intake
Response** and messages the patient. When they submit it in the portal, the answers are
written back into the patient's allergies, medical conditions, smoking status, pregnancy
flag and caries risk — the medical history updates itself rather than being retyped.

### 2. Scheduling

Every appointment passes through the slot engine before it saves:

- practitioner licence is in date, otherwise the booking is refused
- practitioner, operatory and patient are all free for the full duration
- practitioner is not on leave or in an admin block
- the booking respects the minimum lead time and booking horizon

If **smart overbooking** is on and the clashing appointment scores above the risk
threshold, the double-booking is allowed and flagged rather than blocked.

Cancelling or marking a no-show releases the slot. A background job ranks the waitlist by
priority, practitioner match, arrival feasibility, duration fit and waiting time, then
messages the best three candidates.

### 3. The no-show model

Fourteen weighted behavioural features — prior no-shows, late cancellations, first visit,
lead time, day and hour of the slot, confirmation state, reachable contact channel,
outstanding balance, gap since last visit, treatment value, insurance status, prior
reschedules.

The score is transparent: the driving factors are written onto the appointment in plain
language, so the front desk knows *why* a patient is high risk and what to do about it.

Weekly, `recalibrate_weights()` compares each feature's realised no-show rate against the
practice's base rate and reweights by the observed lift. Features that do not discriminate
decay toward zero. The **No Show Risk Model Accuracy** report shows the calibration gap.

### 4. Clinical visit

```
Arrived ──► In Operatory ──► Clinical Note (SOAP) ──► Treatment Plan ──► Clinical Procedure
                  │                                                            │
                  │                                            ┌───────────────┼───────────────┐
                  │                                            ▼               ▼               ▼
                  │                                    Odontogram update  Stock Entry    Sales Invoice
                  │                                                       (Material       + Insurance
                  │                                                        Issue)           Claim
                  └──► wait time captured (arrival → seating)
```

Completing a procedure updates the odontogram automatically: an extraction sets the tooth
to Extracted, a root canal sets Root Canal Treated, a crown sets Crowned, and so on.

### 5. Treatment planning and case acceptance

Plans are phased — emergency, disease control, definitive, rehabilitation, maintenance —
and support **alternative groups**, so implant-versus-bridge appears as two mutually
exclusive options and the system refuses to accept both.

Every line is priced against the patient's primary policy: the most specific coverage rule
wins (exact procedure, then category, then ancestor category), then waiting periods,
frequency limits, annual maximum and out-of-network reduction apply in order. The patient
sees one number — their share.

From the plan you can generate a pre-authorisation, build a financing schedule as a
**Patient Payment Plan**, or push the next accepted phase straight into the diary.

### 6. Periodontal charting

Six sites per tooth: probing depth, recession, bleeding, plaque, suppuration, mobility and
furcation. CAL is computed per aspect; BOP percentage, plaque index, mean PD, mean CAL and
sites ≥5 mm derive on save.

Staging and grading follow the 2018 AAP/EFP world workshop — stage from interdental CAL
with complexity upgrades for deep pockets, furcation and tooth loss; grade primarily from
the bone-loss-to-age ratio, modified by smoking and diabetes. The resulting diagnosis reads
like a clinician wrote it — *"Generalized periodontitis, Stage III, Grade C"* — with a
therapy recommendation attached.

The perio risk band is pushed back onto the patient, which in turn shortens their recall
interval.

### 7. Sterilisation traceability

Most dental software treats this as a paper logbook. Here it is an enforced chain.

```
Instrument Kit (what belongs on the tray)
        │
Instrument Tray (physical barcode, cycle count, sterile-until date)
        │
Sterilization Cycle (temperature, hold time, chemical + biological indicators)
        │
Clinical Procedure (trays scanned at the chair)
        │
Patient
```

On submitting a procedure the system **blocks** any tray that is retired, has no passed
cycle, or whose sterility has expired. Cycle parameters are validated against the minimum
validated conditions for the cycle type, so a 134 °C cycle that only reached 128 °C fails
automatically.

When a cycle fails — including a biological indicator that turns positive days later — the
system traces every patient already treated with trays from that load, quarantines the
trays, raises a **Clinical Incident** flagged as reportable, and lists the affected
patients by name.

The same chain works in reverse for materials: `trace_batch()` answers "which patients
received lot X" for a manufacturer recall, and implants are captured with UDI-DI, UDI-PI,
lot and serial.

### 8. Prescribing safety

Before a prescription saves, the engine checks allergies (including by drug class and
generic name), interactions against both the new items and the patient's current
medications, condition conflicts such as NSAIDs with bleeding risk, duplicate therapy
within a class, and pregnancy category D/X.

Severe findings block the prescription unless a clinical override reason is recorded.
Antibiotic prophylaxis requirements surface on the patient banner with the actual regimen.

### 9. Revenue cycle

```
Procedure ──► Sales Invoice (patient) ──► Insurance Claim (payer share)
                                                   │
                            ┌──────────────────────┼──────────────────────┐
                            ▼                      ▼                      ▼
                    Generate payload         Claim Remittance      Denial → Appeal
                    (X12 837D / NPHIES        (835 ERA posts        (copy with
                     FHIR / manual)            to claims)            resubmission count)
                                                   │
                                            Payment Entry against
                                            the Sales Invoice
```

Filing deadlines are computed per payer and warn at ten days. The **Insurance Claim Aging**
report buckets outstanding balances and flags anything at deadline risk.

### 10. Recall and retention

Recall intervals adapt to the patient's caries risk grade. A daily job generates due
recalls, escalates overdue ones through up to three contact attempts across WhatsApp, SMS
or email in the patient's own language, and the **Recall Effectiveness** report shows
conversion by recall type.

---

## Advanced capabilities

**Surface-level odontogram.** Each tooth renders as five clickable SVG surfaces. Colour
encodes condition, dashes mark planned work, badges mark implants and pontics, and notation
switches between FDI, Universal and Palmer live. Double-click a tooth for its full history
and planned work. Click a surface, pick a procedure, and a whole treatment plan builds from
the linked clinical pathway.

**Clinical pathway engine.** Procedures carry protocols. One click turns "molar root canal"
into a sequenced, correctly spaced plan including the crown that should follow it.

**Chair-hour economics.** Operatories carry an hourly operating cost, so the **Chair
Utilisation and Profitability** report shows utilisation, production per chair hour,
operating cost and contribution per chair — the metric that actually drives dental
profitability.

**Radiation dose tracking.** Every radiograph carries an effective dose. Cumulative lifetime
and 12-month exposure plus the repeat-exposure rate are tracked per patient for ALARA and
IR(ME)R compliance.

**Multi-regime insurance.** One Insurance Claim document files as ANSI X12 837D in the US,
as a FHIR R4 bundle through NPHIES in Saudi Arabia, or exports as structured JSON for portal
upload. Eligibility falls back to a deterministic local check when no clearinghouse is
configured, so the feature works offline.

**ZATCA Phase-2 e-invoicing.** TLV QR generation and chained invoice hashing for simplified
tax invoices, switched on per site.

**CAMBRA caries risk.** Disease indicators, risk factors and protective factors score into a
risk level that drives the recall interval and a concrete preventive protocol.

**Lab case management.** Stages, try-in cycles, remake tracking, turnaround analytics and lab
spend by vendor, with Purchase Invoices against the lab's ERPNext Supplier.

**Implant registry.** UDI capture, insertion torque, ISQ, bone quality, loading protocol,
grafting detail, warranty expiry and an implant passport for the patient.

**Multi-channel messaging.** WhatsApp Cloud API, SMS and email with English and Arabic
templates, plus an inbound webhook so replying YES confirms an appointment or claims a
waitlist slot.

**Patient portal.** Online booking with live slot availability, digital intake forms,
treatment-plan review with e-signature, prescriptions, statements and payment plans.

---

## Configuration reference

`Neo Dentiq Settings` controls the behaviour that varies by practice:

| Group | What it governs |
|---|---|
| Scheduling | Slot granularity, lead time, booking horizon, double booking, smart overbooking threshold, waitlist auto-fill |
| Clinical | Consent enforcement, medical history review interval, drug interaction checking and blocking, automatic chart creation, perio auto-staging |
| Inventory | Automatic consumable consumption, chairside warehouse, sterilisation enforcement, UDI capture, expired batch blocking |
| Revenue cycle | Automatic invoicing, income account, cost centre, insurance regime, ZATCA e-invoicing |
| Communication | Recall automation, reminder offsets, channel enablement |

Credentials never live in the app. `nphies_base_url`, `nphies_license_id`, `whatsapp_token`
and `whatsapp_phone_id` are read from `site_config.json`.

---

## Scheduled jobs

| Schedule | Job |
|---|---|
| 07:00 daily | Appointment reminders, expired sterile tray flagging |
| 01:30 daily | No-show rescoring, patient metric refresh |
| Daily | Recall generation and escalation, consent expiry, claim aging, overdue lab cases, waitlist expiry, licence expiry alerts, payment plan reminders |
| Weekly | No-show model recalibration, sterilizer validation alerts |

---

## Reports

| Report | Answers |
|---|---|
| Chair Utilisation and Profitability | Which chair earns its keep, and what each chair hour costs |
| Treatment Plan Case Acceptance | Who presents well, and how much value walks out the door |
| Sterilisation Traceability Audit | Does every procedure trace back to a passed cycle |
| Material and Implant Traceability | Which patients received a recalled lot |
| Insurance Claim Aging | What the payers owe, and what is near a filing deadline |
| Practitioner Production and Commission | Production per hour, lab cost, commission due |
| No Show Risk Model Accuracy | Is the model calibrated against reality |
| Recall Effectiveness | Which recall types actually convert |
| Patient Clinical Passport | A single chronological record: procedures, prescriptions, radiographs, implants, perio charts, consents |

---

## Code map

```
neo_dentiq/
├── hooks.py                    events, scheduler, fixtures, portal routes
├── install.py                  after_install / after_migrate
├── tasks.py                    14 scheduled jobs
├── permissions.py              row-level access for patients and practitioners
├── setup/
│   ├── tooth_data.py           FDI / Universal / Palmer reference
│   ├── master_data.py          all shipped reference data
│   └── install_fixtures.py     idempotent installer, custom fields, workflows
├── utils/
│   ├── scheduling.py           slot engine, conflicts, availability
│   ├── no_show.py              behavioural model + self-recalibration
│   ├── waitlist.py             candidate ranking and slot backfill
│   ├── traceability.py         sterilisation gate, stock consumption, recall tracing
│   ├── drug_safety.py          allergies, interactions, duplication, pregnancy
│   ├── billing.py              ERPNext invoice / payment / dispensing bridge
│   ├── messaging.py            multi-channel, multi-language templates
│   ├── metrics.py              practice KPIs and chair utilisation
│   └── insurance/estimate_coverage.py
├── integrations/               x12, nphies, zatca, whatsapp, generic fallback
├── api/                        booking, chart, clinical, analytics, portal
├── public/js/                  odontogram, perio grid, patient banner
└── www/                        /book and /my-dental
```

---

## Extending it

The integration layer is deliberately thin. To add a payer regime, drop a module into
`neo_dentiq/integrations/`, return a payload from `build_claim_payload`, and add the option
to `insurance_regime` in Neo Dentiq Settings.

The AI-facing hooks — `ai_transcript` and `ai_suggestions` on Clinical Note,
`ai_analysis_status` and `ai_findings` on Radiograph Record — are plain fields with no
vendor assumption. Point them at whichever scribe or caries-detection endpoint you use.

---

MIT licensed.
