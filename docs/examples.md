# Real-World Usage Examples

> Detailed scenarios to guide the implementation of integrated inventory-finance features.

---

## Example 1: Vaccine Purchase & Usage

### Scenario
You bought Gumboro vaccines from Paves Agrovet for 100 birds at KSh 250 on December 1st, 2025. The vaccines need to be used within a week. In 2 days, you vaccinate your 90 birds and record this. The vaccination is tied to a specific flock.

### Step 1: Purchase Recording

**User Flow:**
```
/finance → Record Expense → Medication
→ Select supplier: Paves Agrovet
→ Enter medication name: Gumboro Vaccine
→ Doses purchased: 100
→ Total cost: 250
→ Payment method: M-PESA
→ Expiry date: 2025-12-08 (1 week from purchase)
```

**Database Updates:**
| Table | Field | Value |
|-------|-------|-------|
| `financial_ledger` | amount | 250 |
| `financial_ledger` | direction | OUT |
| `financial_ledger` | category | MEDICATION |
| `inventory_items` | name | Gumboro Vaccine |
| `inventory_items` | type | MEDICATION |
| `inventory_items` | quantity | 100 doses |
| `inventory_items` | expiry_date | 2025-12-08 |

### Step 2: Vaccination Recording

**User Flow (2 days later):**
```
/health → Record Vaccination
→ Select flock: Flock A - Dec 2024
→ Select vaccine: Gumboro Vaccine (100 doses available)
→ Birds vaccinated: 90
→ Vaccinator: Self
→ Notes: "All healthy, no reactions"
```

**Database Updates:**
| Table | Field | Value |
|-------|-------|-------|
| `vaccination_records` | flock_id | 1 (Flock A) |
| `vaccination_records` | vaccine_name | Gumboro Vaccine |
| `vaccination_records` | doses_used | 90 |
| `vaccination_records` | date | 2025-12-03 |
| `inventory_items` | quantity | 10 doses remaining |

### Step 3: Report Generation

**User Flow:**
```
/reports → Health Reports → Vaccination Schedule
```

**Output:**
```
🏥 Flock A - Vaccination History

Date       | Vaccine          | Birds | Next Due
-----------|------------------|-------|----------
2025-12-03 | Gumboro          | 90    | 2026-03-03 (3 months)
2025-11-15 | Newcastle (ND)   | 95    | 2025-02-15 (3 months)

⚠️ Upcoming:
• Newcastle booster due in 60 days
```

---

## Example 2: Multiple Feed Types Purchase & Daily Usage

### Scenario
Your flock needs food. You go to Best Feeds and purchase:
- 2 bags of Growers Mash (70 kg each) at KSh 2,000 per bag
- 5 bags of Layers Mash (50 kg each) at KSh 2,500 per bag

Every day you feed your birds from storage. Some days you use only layers, some days only growers, some days both (e.g., 2 kg growers + 1 kg layers).

### Step 1: Feed Purchase

**User Flow (Single Purchase Session):**
```
/finance → Record Expense → Feed Purchase
→ Select supplier: Best Feeds Ltd
→ How many types of feed? Multiple

[Feed 1]
→ Select/Enter name: Growers Mash
→ Bags: 2
→ Weight per bag: 70 kg  (pre-filled from settings or entered)
→ Price per bag: 2000

[Feed 2]
→ Select/Enter name: Layers Mash  
→ Bags: 5
→ Weight per bag: 50 kg
→ Price per bag: 2500

→ Total: KSh 16,500
→ Payment method: M-PESA
```

**Database Updates:**

**financial_ledger:**
| Date | Amount | Direction | Category | Description |
|------|--------|-----------|----------|-------------|
| 2025-12-18 | 16,500 | OUT | FEED | 2×Growers (140kg) + 5×Layers (250kg) |

**inventory_items:**
| Name | Type | Quantity | Unit | Cost/Unit |
|------|------|----------|------|-----------|
| Growers Mash | FEED | +140 | kg | 14.29 (2000÷70) |
| Layers Mash | FEED | +250 | kg | 50.00 (2500÷50) |

### Step 2: Daily Feeding (Multiple Feed Types)

**User Flow:**
```
/daily → Step 2: Feed

🍽️ What feed did you use today?
→ [Use Multiple Feeds]

[Feed 1]
→ Select: Growers Mash (140 kg available)
→ Amount: 2 kg

[Feed 2]  
→ Select: Layers Mash (250 kg available)
→ Amount: 1 kg

→ [Done Adding Feeds]
```

**Some days - single feed only:**
```
/daily → Step 2: Feed
→ Select: Layers Mash (249 kg available)
→ Amount: 3 kg
→ Continue to mortality step
```

**Database Updates (Multi-feed day):**

**inventory_items:**
| Name | Before | Change | After |
|------|--------|--------|-------|
| Growers Mash | 140 kg | -2 kg | 138 kg |
| Layers Mash | 250 kg | -1 kg | 249 kg |

**inventory_logs:**
| Date | Item | Quantity | Notes |
|------|------|----------|-------|
| 2025-12-18 | Growers Mash | -2 | Daily Feeding |
| 2025-12-18 | Layers Mash | -1 | Daily Feeding |

**daily_entries:**
| Date | feed_used_kg | feed_cost | feed_details |
|------|--------------|-----------|--------------|
| 2025-12-18 | 3.0 | 78.58 | Growers:2kg, Layers:1kg |

---

## Example 3: Equipment Purchase

### Scenario  
You bought 5 drinkers at KSh 500 each and 3 feeders at KSh 1,200 each from Farm Supplies.

**User Flow:**
```
/finance → Record Expense → Equipment
→ Select supplier: Farm Supplies Ltd
→ Equipment type: Drinkers
→ Quantity: 5
→ Price per unit: 500

[Add another?] → Yes

→ Equipment type: Feeders
→ Quantity: 3  
→ Price per unit: 1200

→ Total: KSh 6,100
→ Payment: Cash
```

---

### Example 4: Bird Purchase (Chicks) & Flock Creation

### Scenario
You bought 200 day-old Kuroiler chicks from Kenchic at KSh 150 each. You want to track them as a new flock, noting that 190 are likely Hens and 10 are Roosters (markers).

**User Flow:**
```
/finance → Record Expense → Birds
→ Select supplier: Kenchic Ltd
→ Are you adding to inventory? [Yes, Add to Stock]
→ Select Item: (Auto-skipped if "Chickens" is your only Livestock type)
→ Quantity: 200
→ Total: KSh 30,000
→ Payment: M-PESA

→ Manage Flock?
   [🥚 Yes, Create NEW Flock]
   [➕ Yes, Add to EXISTING Flock]
   
→ Choose: Create NEW Flock
→ Flock Name: "Kuroilers Batch Dec 2024"
→ Breakdown:
   - Total: 200
   - Hens: 190
   - Roosters: 10 (Auto-calculated)
→ Age: 0 weeks (Day-old)
```

**Database Updates:**
- `financial_ledger`: Expense of 30,000
- `flocks`: New flock created with `hens_count=190`, `roosters_count=10`
- `inventory_items`: +200 Chickens (LIVESTOCK)
- `daily_entries`: flock_total updated

### Example 5: Adding Birds to Existing Flock

### Scenario
You bought 5 grown roosters to add to "Batch A".

**User Flow:**
```
/finance → Birds → ... → Quantity: 5
→ Manage Flock? [➕ Yes, Add to EXISTING Flock]
→ Select: Batch A (Current: 100: 95H/5R)
→ Breakdown of NEW birds:
   - Total: 5
   - Hens: 0
   - Roosters: 5
✅ Updates Batch A total to 105 (95H/10R)
```

---

## Key Requirements Derived from Examples

### 1. Multi-Item Purchase Support
- Single expense, multiple inventory updates
- Different bag sizes per feed type
- Auto-calculate cost per unit (price ÷ weight)

### 2. Medication/Vaccine Tracking
- **New table:** `medication_records` or expand `inventory_logs`
- Track expiry dates
- Track usage per flock
- Vaccination schedule with next-due alerts

### 3. Daily Wizard Enhancement
- Support selecting multiple feed items per day
- Track which feeds were used, not just kg
- Store detailed breakdown in `feed_details` JSON or separate `daily_feed_usage` table

### 4. Health Module (New)
- Vaccination recording
- Treatment recording  
- Health alerts for upcoming vaccinations
- Tie health records to specific flocks

### 6. Inventory Management Rules

**New Inventory Items:**
- New inventory items can ONLY be created through a purchase from a vendor
- The **Finance → Record Expense** flow is the single entry point for new items
- Users choose from pre-populated Units of Measure: `ltrs`, `pcs`, `kgs`, `bags`

**Inventory Module (Adjustments Only):**
- The `/inventory` section is strictly for adjusting EXISTING stock
- No "Add New Item" option in inventory module
- Adjustments for: corrections, spoilage, counted discrepancies, gifts received

**Flow Example:**
```
NEW ITEM:
  /finance → Expense → Feed → New Feed Type
  → Name: "Layers Mash"
  → Unit: [kgs ▾]  ← Pre-populated dropdown
  → Bags: 5, Weight: 50kg, Price: 2500
  ✅ Creates inventory item + logs expense

ADJUSTMENT:
  /inventory → View Stock → Layers Mash → Adjust
  → Current: 250 kg
  → Reason: [Spoilage ▾]
  → Adjustment: -10 kg
  → New quantity: 240 kg
```

### 7. Flock Breakdown & Flexible Health
- **Advanced Flock Onboarding**:
  - Input breakdown of Hens vs. Roosters (e.g., 95 Hens, 5 Roosters).
  - Calculate Egg Production % based on HENS count, not total birds.
  - Allow entering "Age in Weeks" to auto-calculate Hatch Date.
- **Flexible Vaccination**:
  - Schedule is a guide, not a rule.
  - Allow skipping vaccines or changing dates.
  - "Next Due" alerts must adapt to the *actual* last vaccination date.

---

**Version:** 1.2  
**Last Updated:** December 2024
