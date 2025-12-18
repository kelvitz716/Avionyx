# Future Improvements & Roadmap - Avionyx

> Comprehensive enhancement roadmap based on the Poultry Lifecycle Documentation and real-world usage scenarios.

---

## 🎯 Priority 1: Contact Trust Score System (Partial)

### Overview
Implement a dynamic trust scoring system (0-100) to track reliability of suppliers and customers. This is critical for making informed business decisions.

> **Status:** Database column exists (`Contact.trust_score`), but UI for viewing/adjusting is not implemented.

### 1.1 Trust Score Events

**For Suppliers:**
| Event | Score Change |
|-------|--------------|
| Delivery delay (1-2 days) | -3 points |
| Delivery delay (3+ days) | -5 points |
| Quality issues (damaged goods) | -10 points |
| Wrong quantity delivered | -5 points |
| Consistent good service (monthly) | +2 points |
| Quick emergency response | +5 points |

**For Customers:**
| Event | Score Change |
|-------|--------------|
| Late payment (1-3 days) | -3 points |
| Late payment (4-7 days) | -5 points |
| Bounced payment/check | -15 points |
| Dispute/complaint | -10 points |
| Consistent purchases (monthly) | +2 points |
| Prompt payment | +1 point |
| Referral brings new customer | +5 points |

### 1.2 Trust Score Thresholds

| Score Range | Status | Meaning |
|-------------|--------|---------|
| 90-100 | 🟢 Excellent | Preferred partner |
| 70-89 | 🟡 Good | Generally reliable |
| 50-69 | 🟠 Fair | Monitor closely |
| 30-49 | 🔴 Poor | High risk |
| 0-29 | ⚫ Critical | Consider blocking |

### 1.3 Implementation Tasks

- [x] **Phase 1 - Manual Tracking** ✅
  - [x] Add `trust_score` column to Contact model (DB Ready) ✅
  - [x] Add trust score display in `/contacts` → View Contact ✅
  - [x] Add `/contacts` → Edit Contact → **Adjust Trust Score** ✅
  - [x] Require reason notes for all adjustments ✅

- [ ] **Phase 2 - Semi-Automatic**
  - [ ] Prompt after transactions: "Rate this transaction (Good/Fair/Poor)"
  - [ ] System suggests score adjustments based on rating
  - [ ] Add transaction warnings for low-trust contacts

- [ ] **Phase 3 - Fully Automatic**
  - [ ] Track payment dates vs. due dates automatically
  - [ ] Monitor product quality through return rates
  - [ ] Auto-adjust scores based on rules engine

### 1.4 Trust Score Report Command
Add `/contacts` → **Trust Report** showing:
- Breakdown by trust tier (Excellent/Good/Fair/Poor)
- Recommended actions for low-trust contacts
- Trends and alerts

---

## 🔗 Priority 2: Integrated Inventory-Finance Flow ✅ IMPLEMENTED

### Overview
Enhanced connection between purchases and inventory providing seamless tracking.

### 2.1 Feed Purchase Integration ✅
Multi-feed purchase flow now supports:
- Single or multiple feed types per purchase
- Bag count and price-per-bag input
- Custom weight per bag (stored in `InventoryItem.bag_weight`)
- Auto-calculate cost per kg
- Automatic inventory updates with logging

### 2.2 Multi-Feed Daily Consumption ✅
Daily wizard now supports:
- Single or multiple feed selection per day
- Stock validation before deduction
- Detailed breakdown stored in `DailyFeedUsage` table
- Summary display of all feeds used

### 2.3 Database Enhancements ✅
New models and columns added:
- `InventoryItem.expiry_date` - For medication/vaccine expiry
- `InventoryItem.bag_weight` - Per-item bag weight in kg
- `Flock.current_count` - Live bird count tracking
- `VaccinationRecord` - Track vaccinations per flock
- `DailyFeedUsage` - Track multiple feeds per daily entry

---


## 🥚 Priority 3: Enhanced Sales Flow

### 3.1 Loose Eggs vs. Crates Mode
Currently the system tracks eggs. Enhance to support both sale modes:

**Loose Eggs Mode:**
```
Bot: Current stock: 175 eggs available
User: Sell 50 eggs at KSh 15 each
Result: Income KSh 750, Stock: 175 → 125
```

**Crates Mode:**
```
Bot: Available: 4 crates (125 eggs ÷ 30 per crate)
User: Sell 3 crates at KSh 400 each
Result: Income KSh 1,200, Stock: 125 → 35 eggs
```

**Implementation Tasks:**
- [x] Add sale mode selection (Loose/Crates) in income flow ✅
- [x] Calculate available crates from egg inventory ✅
- [x] Auto-convert crate sales to egg deductions (1 crate = 30 eggs) ✅
- [x] Add configurable crate size/price in settings ✅

### 3.2 Bird Sales
- [ ] Support selling culled birds and chicks
- [ ] Track bird inventory separately from layers
- [ ] Integrate bird sales with flock management

---

## 📊 Priority 4: Advanced Reporting

### 4.1 Daily Report Enhancements
Expand `/reports` → Daily Report to show:
- Eggs Collected / Broken / Good
- Eggs Sold / Remaining Stock
- Feed Used (kg) with cost
- Mortality count
- **Daily Income** (sum of all sales)
- **Daily Expenses** (if any)

### 4.2 Performance Metrics Dashboard
Add new performance tracking:
- **Egg production rate:** eggs per day per bird
- **Feed conversion ratio:** kg of feed per egg produced
- **Mortality rate trends:** percentage over weekly periods
- **Revenue per bird per day:** profitability metric

**Implementation Tasks:**
- [x] Add `/reports` → **Performance Metrics** (Production Insights) ✅
- [x] Calculate and display KPIs with trend indicators (Laying Rate, Feed Efficiency) ✅
- [ ] Add visual sparkline-style text charts

### 4.3 Data Export ✅
- [x] **CSV Export:** Download transactions, inventory, and daily entries ✅
- [ ] **PDF Reports:** Generate professional monthly summaries
- [ ] **Date Range Filters:** Custom period selection for all exports

---

## ⚠️ Priority 5: Proactive Alerts ✅ (Basic)

### 5.1 Low Stock Alerts ✅
**Current Status:** Implemented in `alerts.py`

**Enhancements:**
- [ ] Configurable thresholds per item type
- [ ] Scheduled daily stock checks
- [ ] Push notifications via Telegram (not just in-bot messages)

**Example Alert:**
```
⚠️ Low Stock Alert
Layer Mash is at 8kg (below 10kg threshold). Time to restock!
```

### 5.2 Performance Anomaly Detection ✅
- [x] Alert on significant production drops (>20% from rolling average) ✅
- [ ] Alert on unusual mortality spikes
- [ ] Trend-based warnings (declining production over 7 days)

### 5.3 Payment Reminders
- [ ] Track pending payments from customers (credit sales)
- [ ] Send due date reminders
- [ ] Alert on overdue payments (affects trust score)

---

## 🛠 Technical Improvements

### 6.1 Database & Migrations
- [x] **Alembic Migrations:** Basic setup complete ✅
- [ ] **PostgreSQL Support:** Production-ready scaling option
- [x] **Database Backups:** Automated script available (`scripts/backup.sh`) ✅

### 6.2 Testing & Quality Assurance
- [ ] **Unit Tests:** `pytest` suite covering:
  - Database model integrity
  - Business logic calculations
  - Bot command handlers (mocked)
- [ ] **Integration Tests:** End-to-end flow testing
- [ ] **CI/CD:** GitHub Actions for linting (`flake8`, `black`) and tests

### 6.3 Deployment
- [x] **Dockerization:** Complete ✅
- [x] **systemd Service:** Documentation available ✅
- [x] **Deploy Script:** One-click setup (`scripts/deploy.sh`) ✅
- [ ] **Kubernetes Manifests:** For scaled deployments
- [ ] **Health Check Endpoint:** HTTP endpoint for monitoring

### 6.4 Code Quality
- [ ] Type hints across all modules
- [ ] Docstrings for all public functions
- [ ] Consistent error handling patterns
- [ ] Centralized logging configuration

---

## 🎨 UX / UI Improvements

### 7.1 Navigation Enhancements
- [ ] Breadcrumb-style state tracking (show current menu path)
- [ ] Quick actions from main menu (most-used operations)
- [ ] Keyboard shortcut hints in messages

### 7.2 Data Entry Improvements
- [x] Input validation with helpful error messages ✅
- [x] Confirmation dialogs for destructive actions ✅
- [ ] Undo/Edit last entry within 5 minutes

### 7.3 Web Dashboard (Future)
A companion web interface for:
- Data visualization with charts
- Bulk data entry via forms
- User management and permissions

### 7.4 Localization
- [ ] Support for Swahili (primary)
- [ ] Support for other regional languages
- [ ] Configurable currency symbols and formats

---

## 👥 Multi-User & Permissions

### 8.1 User Roles
| Role | Permissions |
|------|-------------|
| Admin | Full access, settings, reports |
| Manager | All data entry, view reports |
| Staff | Daily entries only, no finance |

### 8.2 Implementation Tasks
- [ ] Add `users` table with role field
- [ ] Role-based menu filtering
- [ ] Audit log with user attribution
- [ ] Multi-farm support (separate databases per farm)

---

## 🔄 Workflow Automation

### 9.1 Scheduled Tasks
- [ ] **Morning Reminder:** Prompt to start daily wizard at configured time
- [ ] **Weekly Summary:** Auto-generate and send weekly performance report
- [ ] **Monthly Reports:** Auto-generate P&L at month end

### 9.2 Smart Suggestions
- [ ] Predict feed reorder dates based on consumption
- [ ] Suggest optimal pricing based on market trends
- [ ] Recommend flock management actions based on age/performance

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Trust Score System | High | Medium | P1 |
| Integrated Inv-Finance | High | Medium | P1 |
| Enhanced Sales Flow | High | Low | P2 |
| Performance Metrics | Medium | Low | P2 |
| Data Export | Medium | Medium | P3 |
| Multi-User Support | High | High | P4 |
| Web Dashboard | High | High | P5 |

---

**Version:** 3.0  
**Last Updated:** December 2024  
**Based On:** Avionyx_Poultry_Lifecycle_Documentation.md
