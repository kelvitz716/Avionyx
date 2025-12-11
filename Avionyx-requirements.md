# Chicken Management System Bot — Requirements Document

**Version:** 1.2
**Status:** Approved for Implementation

---

## 1. Project Overview
The **Chicken Management System Bot** is a lightweight, fully standalone Telegram bot designed to help small to mid-scale poultry keepers record, track, and analyze daily farm activities. 

### Key Objectives
- **Simplicity:** Replace physical notebooks and complex software.
- **Speed:** Optimized for fast data entry (< 15 seconds per record).
- **Independence:** Runs locally (offline-friendly), zero external dependencies, no sensors required.
- **Aesthetics:** Minimalistic, stylish, Telegram-first UI.

## 2. Target User
- **Profile:** Small/medium poultry farmers using Telegram daily.
- **Needs:** Quick record-keeping, daily insights, reliable data storage.
- **Tech Level:** Low to medium; prefers simplicity over feature-bloat.

---

## 3. Design Philosophy
- **Minimalistic UI:** Clean, breathable layout with thin whitespace separators.
- **Button-First Navigation:** Extensive use of inline keyboards to minimize typing.
- **One-Action-Per-Screen:** Focus on speed and clarity.
- **Aesthetics:** Soft monochrome icons, subtle emojis (🐔, 🥚), elegant typography.
- **Navigation:** global **⬅ Back** and **🏠 Home** buttons on deep menus.

---

## 4. Core System Modules

### 4.1. Egg Collection
**Features:**
- Record total eggs collected.
- Record broken eggs.
- **Automatic:** Calculate "Good Eggs" (`Total - Broken`).
- Edit/Undo entries.

**UI Style:**
- Numeric input pad or quick entry.
- Success Message: *"✔️ Eggs recorded. Good job."*

### 4.2. Sales Module
**Features:**
- Sell by **Per Egg** or **Per Crate**.
- **Automatic:** Calculate revenue based on dynamic price configuration.
- Breakdown display: Eggs sold, crates sold, total revenue.

**Configuration Dependencies:**
- `price_per_egg`
- `price_per_crate` (Overrules egg price if crate mode selected)
- `crate_size` (Default: 30)

### 4.3. Feed Management
**Features:**
- Input modes: **kg**, **bags**, or **fraction of bag** (e.g., 0.5 bag).
- **Automatic:** Convert all inputs to kg for storage.
- **Automatic:** Calculate daily feed cost.

**Configuration Dependencies:**
- `feed_bag_weight` (kg)
- `feed_bag_cost`
- `feed_unit_preference` (Default input mode)

### 4.4. Mortality Tracking
**Features:**
- Record deaths.
- Select Reason: Sickness, Predator, Accident, Unknown, or Custom.
- **Automatic:** Deduct from global flock count.

**UI Style:**
- Soft, empathetic tone (e.g., *"Sorry for the loss. Entry saved."*).

### 4.5. Flock Count Module
**Features:**
- **Add Birds:** Sales IN, Hatchlings.
- **Remove Birds:** Sales OUT, Transfers.
- **Record Mortality:** (Links to Mortality Module).
- **Logic:** `Current = Previous + Added - Removed - Mortality`.
- **View:** Current flock total.

### 4.6. Reporting & Insights
**Features:**
- **Summaries:** Daily, Weekly, Monthly.
- **Visuals:** Text-based/ASCII charts for trends (e.g., Egg production over 7 days).
- **History:** Paginated view of past records.

**Sample Daily Summary:**
```text
🐓 Daily Farm Summary — Jan 12
———————————————
🥚 Eggs: 27 (2 broken)
💰 Sales: 500 Ksh
🍽️ Feed: 2.0 kg
⚰️ Deaths: 0
🐥 Flock: 57 birds
```

---

## 5. System Settings & Configuration
The system must be fully configurable via a Settings Menu.

### 5.1 Pricing & Units
- **Egg Pricing:** Price per egg, Price per crate.
- **Feed Settings:** Bag weight, Bag cost, Unit preference (kg/bag).
- **Crate Size:** Number of eggs per crate.

### 5.2 Flock Settings
- Initial flock count.
- Breed information (optional).
- Custom mortality reasons.

### 5.3 System
- Backup frequency.
- Pagination size (items per page).
- Data export (CSV/JSON).

---

## 6. User Experience Flow

### 6.1 Navigation Structure
```text
Home
 ├─ Egg Collection
 ├─ Sales
 ├─ Feed Usage
 ├─ Mortality
 ├─ Flock Count
 ├─ Reports
 │   ├─ Daily / Weekly / Monthly
 │   └─ History (Paginated)
 └─ Settings
     ├─ Pricing
     ├─ Flock
     └─ System
```

### 6.2 Pagination
For lists (History, Logs), implementation must include:
- `Entry 3/10` indicator.
- `⬅ Prev | Next ➡` controls.

---

## 7. Data Model
**DailyEntry Schema:**
- `date`: Date
- `eggs_total`: Int
- `eggs_broken`: Int
- `eggs_good`: Int (Computed)
- `eggs_sold`: Int
- `crates_sold`: Int
- `revenue`: Float
- `feed_used_kg`: Float
- `feed_cost`: Float
- `mortality_count`: Int
- `mortality_reason`: String
- `flock_total`: Int

**SystemSettings Schema:**
- `price_per_egg`, `price_per_crate`, `crate_size`
- `feed_bag_weight`, `feed_bag_cost`, `feed_unit`
- `last_backup_date`

---

## 8. Non-Functional Requirements
- **Performance:** Response time < 200ms.
- **Storage:** Local SQLite or JSON.
- **Reliability:** Auto-backup daily.
- **Privacy:** Local-only data by default.
- **Deployment:** Python runtime on Linux/Windows/macOS (initially local).

---

## 9. Future Roadmap (v2)
- PDF Reports.
- Cloud Backup (Google Drive/Dropbox).
- Multi-user support.
- Photo attachments (Receipts, Injury logs).