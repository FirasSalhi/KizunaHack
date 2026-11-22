# Feature Specification: FARMLINK Platform — Web Dashboard and Mobile Version

**Feature Branch**: `001-farmlink-platform`

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: "Plan the implementation of a full solution: a Next.js web dashboard
plus a mobile version of it, for FARMLINK (smart circular farm platform, with ROOTLOOP water
recovery and underground irrigation as its centerpiece). Decide the backend framework and
database and how the mobile version is delivered. Use the open repository RaziSnihaa/is9ini as
the reference for the interface layer and data models where needed."

## Context: what the reference implementation already provides

The reference repository (Is9ini, a single smart greenhouse) already delivers, for **one device
and one site**: owner/viewer sign-in; live readings of soil moisture, air temperature, humidity
and light; a five-state plant "mood"; pump state and water used today; an event log; editable
irrigation thresholds bounded by hard water caps (150 ml per run, 600 ml per day); signed
"water now" and "set mode" commands; and a plant scanner that identifies a plant from a photo,
assesses leaf health, returns a care sheet, and can apply that plant's needs as thresholds.

FARMLINK generalizes this to **many farms, many devices, more sensor types**, a web dashboard
and a phone experience, and adds the decision-support modules described below. The user
stories are ordered so that the reference capabilities are carried over first.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Monitor my farm live, on the web and on my phone (Priority: P1), MVP

A farmer signs in and immediately sees the current state of their farm: each device's latest
soil moisture, air temperature, humidity and light, a plain-language status for the crop
(happy, thirsty, too wet, too hot, sensor problem), whether the pump is running, water used
today, and whether each device is online. Values update by themselves without reloading. A
history chart shows the last hour, day, week or month, and an event log lists what happened
(status changes, watering started/stopped, commands, logins). The same information is usable on
a laptop browser and on a phone.

**Why this priority**: This is the reference implementation's core value and the foundation every
other module displays into. With only this story, a farmer can already watch a ROOTLOOP
prototype or greenhouse remotely.

**Independent Test**: Run the device simulator against a seeded farm, sign in as the viewer on a
desktop browser and on a 360 px phone viewport, and confirm readings change within seconds, the
offline badge appears when the simulator stops, and history and events render.

**Acceptance Scenarios**:

1. **Given** a farm with one online device, **When** a member signs in, **Then** they see that
   device's latest readings, status, pump state, water used today, and an "online" indicator.
2. **Given** the dashboard is open, **When** the device sends a new reading, **Then** the
   displayed values update within 3 seconds without a page reload.
3. **Given** a device has not reported for longer than its expected interval, **When** a member
   views it, **Then** it is shown as offline with the time of the last reading.
4. **Given** a member chooses a history range (hour, day, week, month), **When** the chart
   loads, **Then** it shows readings for that range for the selected device.
5. **Given** a member of farm A, **When** they try to open any data of farm B, **Then** access is
   refused and nothing about farm B is revealed.
6. **Given** a phone-width screen, **When** the member uses every screen in this story, **Then**
   all content is reachable without horizontal scrolling.

---

### User Story 2 — Control irrigation safely (Priority: P2)

A farm owner (or an operator they trust) can start a watering run now, switch a device between
automatic and manual mode, and edit irrigation thresholds (dry and wet soil levels, temperature
range, per-run and per-day water limits). The platform refuses values beyond the hard safety
limits, warns when a command will be refused by the device (for example, soil already wet), and
records who did what. Viewers see the controls' state but cannot change anything.

**Why this priority**: Remote control is what turns monitoring into a management tool, but it is
only acceptable once it is provably safe.

**Independent Test**: With the simulator running, sign in as owner, change thresholds and send
"water now"; confirm the simulated device receives a verifiable command, waters within limits,
and the event log records it. Repeat as viewer and confirm every control is refused.

**Acceptance Scenarios**:

1. **Given** an owner, **When** they set a per-run limit above the hard limit, **Then** the
   change is rejected with an explanation and nothing is sent to the device.
2. **Given** an owner, **When** they set the dry threshold equal to or above the wet threshold,
   **Then** the change is rejected.
3. **Given** an owner and an online device, **When** they press "water now", **Then** the device
   receives an authenticated command, and the event log shows the owner's name and the command.
4. **Given** soil is already too wet, **When** an owner presses "water now", **Then** they are
   warned that the device will refuse to water.
5. **Given** a viewer, **When** they attempt any control action (including by calling the
   service directly), **Then** it is refused.
6. **Given** a command that is replayed or arrives too late, **When** the device receives it,
   **Then** the device ignores it.
7. **Given** the member's phone is offline, **When** they try to send a control command,
   **Then** the action is unavailable and nothing is queued for later.

---

### User Story 3 — Manage my farms, fields, devices and people (Priority: P2)

An owner creates a farm, describes its fields (name, area, soil type, location), registers a
device to a field and receives that device's one-time credential, and invites other people as
operator or viewer. A person can belong to several farms and switch between them.

**Why this priority**: The reference implementation hard-codes one site, one device and two
accounts. Every multi-farm capability depends on this.

**Independent Test**: As a new owner, create a farm and field, register a device, configure the
simulator with the issued credential, and see its readings appear (US1). Invite a viewer and
confirm their access is limited to that farm.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** they create a farm, **Then** they become its owner.
2. **Given** an owner, **When** they register a device, **Then** a credential is shown once and
   readings signed with it are accepted only for that device.
3. **Given** an owner, **When** they revoke a device credential, **Then** further readings and
   command polls from that device are rejected.
4. **Given** an owner, **When** they invite someone by email as viewer, **Then** that person can
   see the farm after accepting and cannot change anything.
5. **Given** a user in two farms, **When** they switch farm, **Then** every screen shows only the
   selected farm's data.
6. **Given** the last owner of a farm, **When** they try to leave or demote themselves,
   **Then** the action is refused until another owner exists.

---

### User Story 4 — Watch the ROOTLOOP water loop (Priority: P3)

A farmer sees the circular-water system at a glance: collection and treated-water tank levels;
water-quality indicators (pH, salinity/EC, turbidity, water temperature); flow and pipe pressure
during irrigation; and leak detection. Each indicator has a target range. When a value leaves its
range, the platform raises an alert that appears on the dashboard and in the alert list, and
optionally holds automatic irrigation from the treated tank.

**Why this priority**: ROOTLOOP is the project's physical centerpiece, but it depends on US1's
live data path and US3's devices.

**Independent Test**: Use the simulator's water-loop profile to push a turbidity spike and a
falling tank level; confirm both alerts are raised, displayed, and cleared when values recover.

**Acceptance Scenarios**:

1. **Given** a device reporting tank and water-quality channels, **When** a member opens the
   water view, **Then** each tank level and indicator shows its value, target range and status.
2. **Given** turbidity rises above its range, **When** the reading arrives, **Then** an alert is
   raised once (not once per reading) and cleared when the value returns to range.
3. **Given** a leak sensor triggers, **When** the reading arrives, **Then** a high-severity alert
   is raised and the pump is shown as locked if the device reports so.
4. **Given** any water-quality view, **When** it is displayed, **Then** it states that the
   indicators are monitoring values and not a certification of water safety.
5. **Given** an owner, **When** they edit an indicator's target range, **Then** future alerts use
   the new range and the change is logged.

---

### User Story 5 — Scan a plant with my phone and track crop health (Priority: P3)

A member takes a photo of a plant or leaf with their phone camera (or uploads one on the web).
The platform returns the likely species with its confidence, alternatives, leaf-health status
with possible diseases and suggested actions, and a care sheet. Uncertain results are labeled as
such. Scans are kept in a history with their photos; the author or an owner can correct or delete
a scan; an owner can apply a plant's recommended thresholds to a field (through US2's safe path).

**Why this priority**: Already built in the reference implementation; high demonstration value;
depends only on US1/US3 foundations.

**Independent Test**: Upload the reference test photos, confirm species, confidence, health,
and history entries; correct one scan; apply recommended thresholds and confirm they pass the
hard-limit validation.

**Acceptance Scenarios**:

1. **Given** a phone, **When** the member taps "scan", **Then** the camera opens directly and the
   photo is submitted.
2. **Given** a photo, **When** identification completes, **Then** the result shows species,
   confidence, the engine used, alternatives, and health status.
3. **Given** a low-confidence result, **When** it is displayed, **Then** it is marked "uncertain"
   and suggests checking alternatives.
4. **Given** a scan, **When** its author or an owner selects a different species, **Then** the
   scan is updated and the original AI result is kept for reference.
5. **Given** a care sheet with recommended thresholds, **When** an owner or operator applies it to a field,
   **Then** thresholds are validated against hard limits exactly as in US2.
6. **Given** the identification service is unavailable, **When** a member scans, **Then** they are
   told clearly and the photo is not lost.

---

### User Story 6 — Use it in the field with a weak or no connection (Priority: P4)

A farmer adds FARMLINK to their phone's home screen and opens it like an app. When the network
drops, they still see the last synced readings, alerts and history with the data age shown.
Photos taken for scanning while offline are queued and submitted automatically when the
connection returns. Control actions are clearly disabled while offline.

**Why this priority**: Important for real field use, but layered on top of the stories above.

**Independent Test**: Load the dashboard, switch the phone to airplane mode, reopen it from the
home screen, confirm cached data and age display; take a scan photo; restore network and confirm
the scan is processed exactly once.

**Acceptance Scenarios**:

1. **Given** a supported phone browser, **When** the member chooses to install, **Then** the app
   opens full-screen from the home screen.
2. **Given** the member previously loaded the dashboard, **When** they open it offline, **Then**
   last-known readings appear with "last updated" time.
3. **Given** a scan taken offline, **When** connectivity returns, **Then** it is submitted once and
   its result appears in history.
4. **Given** offline state, **When** the member views controls, **Then** they are disabled with an
   explanation.

---

### User Story 7 — See my farm's energy (Priority: P4)

A farmer sees solar production, battery level, and pump/equipment consumption over time, and is
warned when battery is too low for a planned irrigation run.

**Why this priority**: Supports the solar/agrivoltaic module; uses the same reading pipeline as
US1/US4 with new channel types.

**Independent Test**: Use the simulator energy profile; confirm production, battery and
consumption charts, and the low-battery warning when starting irrigation.

**Acceptance Scenarios**:

1. **Given** a device reporting energy channels, **When** a member opens the energy view, **Then**
   they see current production, battery level and consumption, and a daily total.
2. **Given** battery below its configured minimum, **When** an owner starts irrigation, **Then**
   they are warned, and the device's own low-battery protection is shown if it refuses.

---

### User Story 8 — Choose what to plant (Priority: P5)

Before planting, a farmer enters a field's location, soil type, area, available water and budget.
The platform returns a ranked list of suitable crops with, for each, its water needs compared with
available water, climate suitability, indicative costs, indicative market price and demand, risks,
and the assumptions used. It can also suggest compatible crop pairings for the same area. Results
are clearly estimates, not guarantees.

**Why this priority**: High business value but depends on reference data and external data that
must be sourced and validated.

**Independent Test**: With seeded crop reference data and sample price data, enter a field profile
and confirm a ranked list with visible basis for each score; change available water and confirm
the ranking changes accordingly.

**Acceptance Scenarios**:

1. **Given** a field profile, **When** the farmer requests recommendations, **Then** at least the
   top crops are listed with score, water fit, climate fit, cost and market indicators, and
   assumptions.
2. **Given** reduced available water, **When** recommendations are recalculated, **Then** crops
   whose needs exceed available water are ranked lower or flagged.
3. **Given** any recommendation, **When** it is displayed, **Then** the data sources and their
   dates are shown.
4. **Given** a chosen crop, **When** the farmer asks for companions, **Then** compatible pairings
   are shown with their reasons (water, roots, light) and a note that local validation is needed.

---

### User Story 9 — Protect my harvest in storage (Priority: P5)

A farmer registers a storage or drying area, links temperature/humidity sensors to it, and selects
the stored crop. The platform shows conditions against crop-specific target ranges, alerts when
conditions leave them, and gives handling and storage guidance.

**Why this priority**: Reuses the reading and alert pipeline (US1, US4) with new context.

**Independent Test**: Register a storage unit with the simulator's storage profile; push humidity
above the stored crop's range; confirm the alert and guidance.

**Acceptance Scenarios**:

1. **Given** a storage unit with a stored crop, **When** a member views it, **Then** temperature and
   humidity are shown against that crop's target ranges.
2. **Given** humidity above range for longer than the configured duration, **When** it persists,
   **Then** an alert is raised with crop-specific guidance.

---

### User Story 10 — Find buyers and suppliers (Priority: P6)

A farmer publishes produce they have available (crop, quantity, quality, location, availability
date). Buyers publish what they need; suppliers publish seeds, equipment and services. Each party
can browse and filter listings and contact the other party. Indicative market prices and trends
are displayed per crop.

**Why this priority**: Commercially meaningful but introduces new user types and moderation needs;
it does not depend on hardware.

**Independent Test**: Seed sample listings; a farmer posts produce, a buyer finds it by crop and
region and sends a contact request; the farmer sees the request.

**Acceptance Scenarios**:

1. **Given** a farmer, **When** they publish a produce listing, **Then** it appears in search
   results filtered by crop and region.
2. **Given** a buyer, **When** they contact a listing's owner, **Then** the owner is notified and
   contact details are shared only with the owner's consent.
3. **Given** a listing, **When** its owner marks it sold or it passes its end date, **Then** it no
   longer appears in search.

---

### Edge Cases

- A device reports values outside physical range (for example, humidity 140%): the reading is
  rejected and a security/quality event is logged; it never reaches charts or alerts.
- A device's clock is wrong: the server's receive time is authoritative for storage.
- Two owners change thresholds at the same time: the later change wins and both are logged; the
  device receives the final settings.
- The same device credential is used from two places: readings are accepted only with a valid
  signature; repeated failures raise a security alert.
- A member is removed from a farm while their dashboard is open: their live connection is closed
  and subsequent requests are refused.
- A session expires while offline: cached read data remains visible; the member must sign in
  again before any write.
- A photo is too large or not an image: the member is told before upload where possible, and the
  service rejects it with a clear message.
- The live connection drops: the client falls back to periodic refresh and shows that live updates
  are paused.
- A device was offline for hours and uploads buffered readings: they are stored at their original
  measurement times if within an accepted window, and alerts are not re-raised for stale data.
- External data (weather, prices) is unavailable: crop planning shows the last known data with its
  date, or states that the input is missing; it never shows invented values.

## Requirements *(mandatory)*

### Functional Requirements

**Identity and access**

- **FR-001**: System MUST let users sign in with email and password and sign out on any device.
- **FR-002**: System MUST support farm membership with the roles owner, operator and viewer;
  owners manage the farm and its members; operators may control irrigation and settings; viewers
  may only read.
- **FR-003**: System MUST authorize every read and write on the server against the caller's
  membership and role for the farm the data belongs to.
- **FR-004**: System MUST allow owners to invite members by email, change their roles, and remove
  them, while always keeping at least one owner per farm.
- **FR-005**: System MUST keep users signed in across app restarts for a bounded period and allow
  sessions to be revoked.
- **FR-006**: System MUST record an audit trail of sign-ins, failed sign-ins, membership changes,
  setting changes, commands and rejected device messages.

**Farms, fields and devices**

- **FR-007**: Owners MUST be able to create and edit farms and fields (name, area, soil type,
  location, crop).
- **FR-008**: Owners MUST be able to register devices to a field, receive a per-device credential
  shown once, rotate it, and revoke it.
- **FR-009**: Each device MUST declare which measurement channels it reports (for example soil
  moisture, tank level, pH, battery) so screens show only what exists.

**Readings and live data**

- **FR-010**: System MUST accept readings only when signed with the sending device's valid
  credential, and MUST reject out-of-range values.
- **FR-011**: System MUST store readings with their measurement time and keep them available for
  history views of at least the last 30 days at full resolution and longer at reduced resolution.
- **FR-012**: System MUST push new readings, status changes and alerts to connected members of
  the farm within 3 seconds of receipt.
- **FR-013**: System MUST show a device as offline when it has not reported within its expected
  interval.
- **FR-014**: System MUST record events for status changes, pump start/stop, commands, setting
  changes and device-reported events, and let members filter them by time range.

**Control and safety**

- **FR-015**: Owners and operators MUST be able to send "water now" and "set mode
  (auto/manual)" commands to a device.
- **FR-016**: System MUST enforce hard limits on water per run and per day that no user setting
  can exceed, and MUST reject (not silently adjust) settings beyond them.
- **FR-017**: System MUST sign every command for the target device with a timestamp and a sequence
  number that never repeats or decreases, including after a restart.
- **FR-018**: System MUST deliver commands over the device's live channel when available and keep
  them for the device to fetch otherwise, discarding them once expired.
- **FR-019**: System MUST NOT allow commands to be queued on a client while it is offline.

**ROOTLOOP water loop, energy and storage**

- **FR-020**: System MUST display tank levels, water-quality indicators (pH, EC, turbidity, water
  temperature), flow, pressure and leak state for devices that report them.
- **FR-021**: System MUST let owners configure target ranges per indicator and raise one alert
  when a value leaves its range for longer than a configured duration, clearing it on recovery.
- **FR-022**: System MUST display energy production, battery level and consumption for devices
  that report them, and warn before irrigation when battery is below the configured minimum.
- **FR-023**: System MUST let owners register storage areas, assign sensors and a stored crop, and
  alert when conditions leave that crop's target ranges.

**Plant scanning and crop health**

- **FR-024**: Members MUST be able to submit a plant photo from the phone camera or a file and
  receive species, confidence, alternatives, engine used, health status and care sheet.
- **FR-025**: System MUST label results below the confidence threshold as uncertain.
- **FR-026**: System MUST keep scan history with photos per farm; the author or an owner MAY
  correct or delete a scan; corrections keep the original result.
- **FR-027**: Owners and operators MAY apply a care sheet's recommended thresholds to a field,
  subject to FR-016.

**Decision support and marketplace**

- **FR-028**: System MUST produce ranked crop recommendations for a field profile showing, per
  crop, the basis of the score (water fit, climate fit, cost, market indicators) and data dates.
- **FR-029**: System MUST provide crop compatibility suggestions with reasons and a validation
  notice.
- **FR-030**: System MUST let farmers publish produce listings, buyers publish requests, and
  suppliers publish offers; let all parties search by crop, category and region; and support
  contact requests between parties.
- **FR-031**: System MUST display indicative market prices per crop with their source and date.

**Mobile and offline**

- **FR-032**: Every member-facing screen MUST be usable on a 360 px wide phone screen.
- **FR-033**: The phone experience MUST be installable to the home screen and open full-screen.
- **FR-034**: Previously loaded readings, alerts and history MUST remain viewable offline with the
  data age shown.
- **FR-035**: Scan submissions made offline MUST be queued and submitted exactly once when
  connectivity returns.
- **FR-036**: Interface text MUST be translatable and layouts MUST support right-to-left scripts.
- **FR-037**: Members who opt in on a device MUST receive a web push notification when an alert
  opens on one of their farms, including when the app is closed. Notifications MUST NOT include
  readings or other farm data beyond the alert's title and severity, and opening one MUST lead to
  the alert after sign-in.

### Key Entities

- **User**: a person who signs in; name, email, preferred language.
- **Farm**: a farming operation; name, region, owners and members.
- **Membership**: a user's role (owner, operator, viewer) in one farm.
- **Field**: an area of a farm; name, area, soil type, location, current crop.
- **Device**: a controller installed in a field or storage area; identity, credential status,
  declared channels, expected reporting interval, last seen time.
- **Channel**: one measured quantity on a device (for example soil moisture %, tank level %, pH,
  EC, turbidity, flow, pressure, battery voltage); unit, physical range, target range.
- **Reading**: a channel value at a measurement time from a device.
- **Device Status**: the device's computed crop status (the five moods), pump state, mode, water
  used today, at a time.
- **Irrigation Settings**: per-device thresholds and limits, bounded by hard limits.
- **Command**: an instruction to a device; type, value, issuer, sequence number, issue time,
  delivery state.
- **Event**: something that happened on a farm; type, message, related device/user, time.
- **Alert Rule / Alert**: a range condition on a channel, and an occurrence of it with start,
  end, severity and acknowledgement.
- **Plant Scan**: a photo-based identification; author, photo, AI result, correction, time.
- **Crop Profile**: reference data on a crop (water needs, climate ranges, root depth, storage
  ranges, typical diseases).
- **Crop Recommendation**: a ranked result for a field profile with its inputs and data dates.
- **Storage Unit**: a storage or drying area with its stored crop and sensors.
- **Listing**: a produce offer, buyer request or supplier offer, with owner, crop/category,
  quantity, region, dates, status.
- **Contact Request**: a request from one party to another about a listing.
- **Market Price**: an indicative price for a crop at a market and date, with source.
- **Audit Entry**: a security-relevant action with actor, target and time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new reading is visible on every open dashboard of that farm within 3 seconds of
  the device sending it, for at least 95% of readings.
- **SC-002**: A signed-in member reaches their farm's live overview in under 3 seconds on a
  typical 4G phone connection.
- **SC-003**: 100% of attempts to exceed hard water limits, replay a command, or access another
  farm's data are rejected in the automated test suite.
- **SC-004**: A first-time farmer can sign in and find the current soil moisture of a field
  without help in under 1 minute.
- **SC-005**: An owner can register a new device and see its first reading in under 10 minutes,
  following on-screen instructions.
- **SC-006**: Opened offline, the phone experience shows last-known data within 2 seconds.
- **SC-007**: Every screen in US1–US5 passes a check at 360 px width with no horizontal scrolling.
- **SC-008**: A plant scan returns a result in under 10 seconds for 90% of photos on a 4G
  connection.
- **SC-009**: Out-of-range water-quality values raise exactly one alert per excursion.

## Assumptions

- The reference repository's features, thresholds (150 ml/run, 600 ml/day for the greenhouse
  profile), five moods, and plant-scanning engines are the baseline to carry forward. Hard limits
  become per-device-profile values set by the platform, not by farm users.
- Device firmware is developed separately; this feature defines the device-facing protocol and a
  simulator, and the firmware must enforce hard limits independently.
- Email and password is the sign-in method for the first release; social or phone sign-in is out
  of scope.
- Default roles are owner, operator and viewer (operator is new compared with the reference).
- Interface languages at first release: French, Tunisian Derja and English (decided 2026-11-21),
  with right-to-left support built in. Modern Standard Arabic is not required at launch.
  Which script Derja is written in is still open (see Open Questions).
- The marketplace provides listings and contact requests only; payments, orders and delivery are
  out of scope. (See Open Questions.)
- Crop planning, price and weather data come from external or curated sources chosen during
  planning; where no source is available, the module uses clearly labeled sample data.
- Alerts must reach a farmer whose app is closed through web push to the installed PWA
  (decided 2026-11-21). This works on Android and on iPhone (iOS 16.4+) once the app is added to
  the home screen. SMS and native store apps are out of scope.
- No timeline, team size or budget is assumed by this specification.

## Open Questions

These are decisions the specification cannot make on its own. Defaults above are used until they
are answered.

1. **Languages** — *decided 2026-11-21*: French, Tunisian Derja and English. Still open: is Derja
   written in Arabic script (right-to-left) or in Latin script (Arabizi), or both?
2. **Marketplace scope**: Is the marketplace listings-and-contact only, or must it handle orders,
   payments or delivery? The latter adds regulatory, trust and moderation requirements.
3. **Phone alerts** — *decided 2026-11-21*: web push to the installed PWA is enough (FR-037);
   no native wrap.
