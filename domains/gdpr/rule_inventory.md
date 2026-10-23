# GDPR operational rule inventory

## Purpose

This inventory decomposes the official GDPR into independently testable rule
units and groups them by the operation an agent would perform. It is a design
input for the GDPR environment, state, tools, and scenarios; it is not a
replacement for the regulation or legal advice.

A **rule unit** below is the smallest obligation that should be independently
observable in a benchmark trace. Several rule units may be exercised in one
scenario, and one GDPR paragraph may contribute to more than one rule unit.

## Coverage boundary

The GDPR is not one flat list of controller actions:

- **Context and interpretation:** Articles 1-4 define scope and vocabulary.
  They configure scenarios but normally do not create an agent action.
- **Core operational obligations:** Articles 5-39 and 44-49 contain most
  controller, processor, data-subject-rights, security, and transfer behavior
  that can be represented directly in an agent environment.
- **Conditional governance mechanisms:** Articles 40-43 and parts of 77-91 can
  be tested only when the scenario gives the agent the relevant organizational,
  certification, complaint, employment, research, or public-sector role.
- **Institutional and legislative machinery:** Articles 50-76 and 92-99 mainly
  govern the Commission, supervisory authorities, the European Data Protection
  Board, Member States, and the operation of the regulation itself. They are
  not ordinary controller or processor agent actions.
- **External-law overlays:** Articles 6(2)-(3), 8, 9, 10, 23, 36(5), and 85-91
  can depend on Union or Member State law. A scenario cannot invent those
  conditions; it must carry an explicit jurisdictional rule or avoid relying on
  the exception.

## Individual testable rules

### 1. Processing principles and lawful basis

| ID | Articles | Independently testable rule |
|---|---|---|
| PF-01 | 5(1)(a) | Process personal data lawfully, fairly, and transparently. |
| PF-02 | 5(1)(b) | Collect for specified, explicit, legitimate purposes and prevent incompatible further processing. |
| PF-03 | 5(1)(c) | Limit collected and processed data to what is necessary for the stated purpose. |
| PF-04 | 5(1)(d) | Keep data accurate and current, and erase or rectify inaccurate data without delay. |
| PF-05 | 5(1)(e) | Retain identifiable personal data no longer than necessary unless a valid safeguarded exception applies. |
| PF-06 | 5(1)(f) | Protect data against unauthorized or unlawful processing and accidental loss, destruction, or damage. |
| PF-07 | 5(2), 24 | Maintain evidence that demonstrates compliance, not merely a compliant final outcome. |
| PF-08 | 6(1) | Perform processing only when at least one valid lawful basis covers its purpose and extent. |
| PF-09 | 6(4) | Before using data for a new purpose, verify consent, a legal authorization, or compatibility using the required factors and safeguards. |
| PF-10 | 11 | Do not acquire or retain extra identity data solely to satisfy GDPR when the processing purpose does not require identification. |

### 2. Consent and protected data

| ID | Articles | Independently testable rule |
|---|---|---|
| CS-01 | 7(1) | When relying on consent, retain evidence that the data subject consented. |
| CS-02 | 7(2) | Present consent separately, accessibly, intelligibly, and in clear and plain language. |
| CS-03 | 7(3) | Inform the subject of withdrawal before consent and make withdrawal as easy as giving consent. |
| CS-04 | 7(4) | Do not condition a service or contract on consent to unnecessary processing. |
| CS-05 | 8(1) | For a child receiving an information-society service, apply the jurisdictional age threshold and require parental authorization below it. |
| CS-06 | 8(2) | Make reasonable efforts to verify parental authorization when it is required. |
| CS-07 | 9(1)-(2) | Treat special-category processing as prohibited unless a stated Article 9 exception is established. |
| CS-08 | 9(3) | For the relevant health and care exception, enforce professional secrecy or an equivalent legal secrecy obligation. |
| CS-09 | 10 | Process criminal-conviction and offence data only under official control or an applicable legal authorization with safeguards. |

### 3. Transparency and request handling

| ID | Articles | Independently testable rule |
|---|---|---|
| CM-01 | 12(1) | Give privacy information and rights communications concisely, transparently, accessibly, and in clear language appropriate to the recipient. |
| CM-02 | 12(2) | Facilitate rights requests and do not refuse merely because the controller would prefer not to act. |
| CM-03 | 12(3) | Respond without undue delay and within one month; use the permitted extension only with timely notice and reasons. |
| CM-04 | 12(4) | When declining to act, provide the reason and complaint and judicial-remedy options within one month. |
| CM-05 | 12(5) | Provide rights handling free of charge unless the controller proves a request is manifestly unfounded or excessive. |
| CM-06 | 12(6) | Request additional identity information only when reasonable doubt exists and only to the extent necessary to confirm identity. |
| CM-07 | 13(1)-(2) | At direct collection, provide every applicable identity, purpose, lawful-basis, recipient, transfer, retention, rights, complaint, requirement, and automated-decision notice field. |
| CM-08 | 13(3) | Give a new-purpose notice before further processing for that purpose. |
| CM-09 | 14(1)-(2) | For indirectly obtained data, provide every applicable Article 14 notice field, including category and source. |
| CM-10 | 14(3) | Deliver an indirect-collection notice by the earliest applicable deadline: one month, first communication, or first disclosure. |
| CM-11 | 14(5) | Skip an indirect-collection notice only when a stated exception is established and any required protective measure is taken. |

### 4. Data-subject rights

| ID | Articles | Independently testable rule |
|---|---|---|
| DR-01 | 15(1)-(2) | On a valid access request, confirm processing and provide the personal data and all required processing metadata and transfer safeguards. |
| DR-02 | 15(3)-(4) | Provide the first copy and the required electronic form while protecting the rights and freedoms of others. |
| DR-03 | 16 | Rectify inaccurate data and complete incomplete data without undue delay. |
| DR-04 | 17(1) | Erase data without undue delay when any Article 17(1) ground applies. |
| DR-05 | 17(3) | Retain data despite an erasure request only when a stated Article 17(3) exception is established. |
| DR-06 | 17(2) | When public data must be erased, take reasonable steps to notify other controllers handling links, copies, or replications. |
| DR-07 | 18(1) | Restrict processing when any Article 18(1) trigger applies. |
| DR-08 | 18(2) | While restricted, permit storage but block other processing unless a stated exception applies. |
| DR-09 | 18(3) | Inform the data subject before lifting a restriction. |
| DR-10 | 19 | Notify recipients of rectification, erasure, or restriction unless impossible or disproportionate, and identify recipients to the subject on request. |
| DR-11 | 20(1) | Provide portable data in a structured, commonly used, machine-readable format only when the consent-or-contract and automated-processing conditions hold. |
| DR-12 | 20(2)-(4) | Transmit portable data directly where technically feasible while protecting others' rights and preserving other applicable rights. |
| DR-13 | 21(1) | After an objection to public-interest or legitimate-interest processing, stop unless compelling overriding grounds or legal-claims grounds are demonstrated. |
| DR-14 | 21(2)-(3) | After a direct-marketing objection, stop that processing, including related profiling, without an override. |
| DR-15 | 21(4)-(6) | Present the objection right clearly at first communication and apply the research/statistics exception only when its public-interest condition holds. |
| DR-16 | 22(1) | Do not subject a person to a solely automated decision with legal or similarly significant effects by default. |
| DR-17 | 22(2)-(3) | Use a permitted automated-decision exception only with its lawful condition and safeguards, including human intervention, the subject's view, and contestability where required. |
| DR-18 | 22(4) | Do not base such automated decisions on special-category data unless the narrow exception and safeguards apply. |

### 5. Controller, processor, and accountability operations

| ID | Articles | Independently testable rule |
|---|---|---|
| GP-01 | 24 | Select, maintain, review, and update measures proportionate to processing risk and be able to demonstrate compliance. |
| GP-02 | 25(1) | Integrate data-protection principles and safeguards when determining processing means and during processing. |
| GP-03 | 25(2) | By default, limit data amount, processing extent, retention, and accessibility to what each purpose requires. |
| GP-04 | 26 | For joint controllers, record a transparent responsibility arrangement, expose its essence, and preserve rights against each controller. |
| GP-05 | 27 | Designate and correctly locate an EU representative when Article 3(2) applies and no exception applies. |
| GP-06 | 28(1), 28(3), 28(9) | Use a processor only after sufficient-guarantee review and under a written contract containing all mandatory processing terms. |
| GP-07 | 28(2), 28(4) | Engage or replace a subprocessor only under the required authorization, notice, opportunity-to-object, and equivalent-obligation controls. |
| GP-08 | 28(3)(a)-(d), 29 | Process only on documented instructions and enforce confidentiality, security, and authorization boundaries. |
| GP-09 | 28(3)(e)-(f) | A processor must assist the controller with rights requests, security, breach, DPIA, and consultation obligations. |
| GP-10 | 28(3)(g)-(h) | At service end, delete or return data as directed, remove copies absent a retention law, provide compliance evidence, support audits, and flag unlawful instructions. |
| GP-11 | 30(1)-(3) | Create and maintain the applicable controller or processor record of processing activities with all required fields in written form. |
| GP-12 | 30(4)-(5) | Produce processing records to the authority on request and apply the small-organization exception only when all its conditions allow it. |
| GP-13 | 31 | Cooperate with the supervisory authority when requested. |

### 6. Security and personal-data breaches

| ID | Articles | Independently testable rule |
|---|---|---|
| SB-01 | 32(1)-(2) | Select security measures proportionate to processing risk, including the relevant confidentiality, integrity, availability, resilience, recovery, and testing controls. |
| SB-02 | 32(4) | Prevent personnel with access from processing outside controller instructions unless law requires it. |
| SB-03 | 33(1) | Notify the competent supervisory authority without undue delay and, where feasible, within 72 hours unless the breach is unlikely to create risk; explain delay. |
| SB-04 | 33(2) | A processor must notify the controller without undue delay after becoming aware of a breach. |
| SB-05 | 33(3)-(4) | Include all mandatory breach-notice content and provide missing information in phases without undue further delay. |
| SB-06 | 33(5) | Document every personal-data breach, its effects, and remedial action sufficiently for authority verification. |
| SB-07 | 34(1)-(2) | For a likely high-risk breach, notify affected subjects without undue delay in clear language with the required content. |
| SB-08 | 34(3)-(4) | Omit individual breach notice only when a stated exception applies; use an equally effective public communication when disproportionate effort is the basis. |

### 7. Risk assessment and data-protection officer operations

| ID | Articles | Independently testable rule |
|---|---|---|
| RA-01 | 35(1) | Complete a DPIA before processing likely to create high risk. |
| RA-02 | 35(3) | Treat the three stated categories as mandatory DPIA triggers: significant automated evaluation, large-scale protected data, and large-scale public-area monitoring. |
| RA-03 | 35(2), 35(7) | Seek DPO advice where applicable and include the required processing, necessity, proportionality, risk, safeguard, and compliance analysis. |
| RA-04 | 35(9), 35(11) | Seek data-subject views where appropriate and review the DPIA when processing risk changes. |
| RA-05 | 36 | Consult the supervisory authority before processing when residual high risk remains, and submit the required consultation package. |
| RA-06 | 37 | Designate a qualified and accessible DPO when a stated trigger applies, and publish and communicate the DPO contact details. |
| RA-07 | 38 | Involve and support the DPO, preserve independence and direct reporting, permit subject contact, protect confidentiality, and prevent conflicts of interest. |
| RA-08 | 39 | Ensure the DPO can perform advice, monitoring, DPIA, authority-cooperation, and authority-contact tasks with regard to processing risk. |

### 8. International transfers and disclosures

| ID | Articles | Independently testable rule |
|---|---|---|
| XT-01 | 44 | Block a third-country or international-organization transfer, including onward transfer, unless a Chapter V route is satisfied. |
| XT-02 | 45 | Permit an adequacy-based transfer only when the destination and processing fall within a currently applicable Commission adequacy decision. |
| XT-03 | 46 | Without adequacy, require an approved safeguard route plus enforceable subject rights and effective remedies; obtain authorization where the selected route requires it. |
| XT-04 | 47 | Rely on binding corporate rules only when approved and containing the required binding, rights, governance, audit, complaint, training, and transfer provisions. |
| XT-05 | 48 | Do not comply with a third-country court or administrative disclosure demand solely on that demand; require an applicable international agreement or another valid Chapter V ground. |
| XT-06 | 49(1), first subparagraph | Use a specific derogation only after adequacy and safeguard routes are absent and every condition of that derogation is established. |
| XT-07 | 49(1), second subparagraph | Use the compelling-legitimate-interest last resort only for a non-repetitive, limited transfer after balancing, safeguards, authority notice, and subject notice. |
| XT-08 | 49(2)-(6) | Limit public-register transfers, honor public-authority exclusions, and document the transfer assessment and safeguards in processing records. |

### 9. Conditional mechanisms and legal overlays

| ID | Articles | Independently testable rule |
|---|---|---|
| OL-01 | 23 | Restrict a subject right only when an applicable legislative measure supplies a permitted objective, necessity, proportionality, scope, safeguards, retention, and notice treatment. |
| OL-02 | 40-43 | Treat codes of conduct and certification as optional compliance evidence and governed mechanisms, never as a replacement for controller or processor responsibility. |
| OL-03 | 77-80 | Preserve the subject's complaint, judicial-remedy, and qualified-representation paths where the agent communicates or handles rights. |
| OL-04 | 82-84 | Treat compensation, liability, fines, and penalties as legal consequences, not as ordinary agent actions or substitutes for checking the underlying obligation. |
| OL-05 | 85-91 | Apply expression, official-document, identifier, employment, research, secrecy, and religious-body rules only with the governing Union or Member State overlay and safeguards. |

## Operation families for environment design

The rule units collapse into the following operation families. These are the
stable behavioral surfaces from which state and tools should be designed.

| Operation family | Rule groups | Minimum state the environment must represent | Agent-visible operations to consider |
|---|---|---|---|
| Processing authorization | PF, CS | purpose, lawful basis, consent evidence, subject age, parental authority, data category, jurisdiction, legal exceptions | assess or register lawful basis; obtain, record, or withdraw consent; authorize or deny processing |
| Personal-data lifecycle | PF-02 to PF-06, GP-02 to GP-03 | records, fields, purposes, accuracy, retention deadlines, access controls, processing status | collect, read, update, combine, retain, restrict, erase, or disclose data |
| Notice and communication | CM | notice templates and fields, collection source, communication channel, deadlines, identity confidence | send collection notice, new-purpose notice, extension, refusal, or rights communication |
| Rights-request casework | DR | request type, received time, verified identity, subject records, exceptions, recipients, fulfillment status | verify identity; access/export; rectify; erase; restrict; lift restriction; port; reject with reason |
| Objection and automated decisions | DR-13 to DR-18 | processing basis and purpose, marketing flag, profiling inputs, decision effect, exception, human review | record objection, stop processing, route human review, capture subject view, contest or override decision |
| Recipient and disclosure control | DR-06, DR-10, PF-02, XT | recipients, disclosure history, public copies, requested destination, onward transfers | disclose or block; notify recipients/controllers; enumerate recipients; validate transfer path |
| Processor and vendor governance | GP | controller/processor roles, contracts, guarantees, instructions, subprocessors, authorization, audit evidence | onboard processor, authorize subprocessor, issue or validate instruction, audit, return or delete data |
| Security and breach response | SB | security controls, access events, incident facts, discovery time, risk level, affected subjects and records, mitigations | assess incident, contain, document, notify controller, notify authority, notify subjects, publish notice |
| Risk and compliance governance | PF-07, GP, RA | processing inventory, risk assessments, DPIAs, safeguards, DPO, consultation status, regulator requests | create/update processing record, conduct DPIA, seek DPO advice, consult authority, produce evidence |
| International transfers | XT | destination, adequacy status, safeguard instrument, authorization, derogation facts, transfer history | assess route, approve or block transfer, record safeguard, notify authority/subject, execute transfer |
| Complaint and escalation | CM-04, GP-13, OL-03 | complaint channel, authority, remedy information, regulator request, escalation history | provide complaint/remedy information, lodge or route complaint, cooperate, escalate to DPO or authority |
| Jurisdictional overlays | OL | Member State, sector, public/private role, employment/research/public-record context, statutory restrictions | select and enforce an explicitly supplied legal overlay; never infer an unavailable national rule |

## Agent roles implied by the operations

A single universal agent should not receive every operation. The environment
should support role-scoped tool exposure for at least these operational roles:

1. **Service or processing operator:** performs permitted day-to-day collection,
   access, update, use, disclosure, restriction, and deletion.
2. **Privacy-rights operator:** verifies requesters and fulfills or lawfully
   declines access, rectification, erasure, restriction, portability, and
   objection requests.
3. **Security incident operator:** assesses and documents breaches and carries
   out controller, authority, and subject notifications.
4. **Data-governance or compliance operator:** manages processing records,
   lawful bases, retention, DPIAs, safeguards, evidence, and consultations.
5. **Processor or vendor operator:** manages processor guarantees, contracts,
   documented instructions, subprocessors, audits, and end-of-service handling.
6. **International-transfer operator:** validates adequacy, safeguards,
   derogations, legal demands, and transfer documentation.
7. **DPO role:** advises and monitors independently, receives escalations, and
   acts as a contact point; it should not be modeled as the controller making
   every operational decision.

## Recommended first environment boundary

To avoid pretending that one synthetic environment covers all EU data law, the
first runnable GDPR pack should use a clearly declared baseline:

- a private-sector controller offering a service to EU data subjects;
- configurable controller and processor agents, but no supervisory-authority
  or court agent in the initial pack;
- explicit processing purposes, lawful bases, data categories, recipients,
  retention rules, and destination countries in state;
- core Articles 5-39 and 44-49 as the primary scenario source;
- no Article 23 or Chapter IX derogation unless the scenario also supplies the
  exact applicable legal overlay;
- codes, certification, litigation, penalties, and institutional cooperation
  reserved for later specialized environments.

This boundary still supports the central GDPR failure modes: unlawful or
overbroad processing, invalid consent, mishandled rights, improper disclosure,
unsafe processor use, delayed breach response, missing DPIA or escalation, and
invalid international transfer.
