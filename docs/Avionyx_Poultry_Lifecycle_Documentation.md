# Avionyx Poultry Management System

**Real-Life Usage Documentation**  
*Complete Lifecycle Examples from Farm to Market*

---

## Introduction

This document provides real-world examples of managing a poultry farm using the Avionyx Telegram bot. Follow along as we demonstrate every feature through the daily operations of a typical Kenyan poultry farmer.

---

## 1. Initial Setup: Adding Your Contacts

### 1.1 Adding a Supplier

Before you can purchase feed or medication, you need to register your suppliers in the system.

| Step | Action |
|------|--------|
| 1 | Send command: `/contacts` |
| 2 | Select: **Add New Contact** |
| 3 | Enter Name: **Best Feeds Ltd** |
| 4 | Select Role: **Supplier** |
| 5 | Enter Phone: **0722123456** |
| **Result** | ✓ Supplier saved in `contacts` table |

**Database Changes:**

| Table | Name | Role | Phone | Trust Score |
|-------|------|------|-------|-------------|
| contacts | Best Feeds Ltd | SUPPLIER | 0722123456 | 100 |

### 1.2 Adding a Customer

Similarly, add your regular customers who buy eggs from you.

**Example: Adding Mama Mboga (local vegetable vendor)**

- **Name:** Mama Mboga
- **Role:** Customer
- **Phone:** 0733456789
- **Initial Trust Score:** 100

---

## 2. Purchasing Feed: The Complete Journey

### 2.1 The Scenario

*Your chickens are running low on feed. You notice you have only 5kg left. You go to your supplier (Best Feeds Ltd) and purchase 2 bags of Layer Mash, each weighing 70kg, at KSh 2,000 per bag.*

### 2.2 Recording the Purchase

| Step | Action & Bot Response |
|------|----------------------|
| 1 | You: `/finance` |
| 2 | Bot: Select transaction type → You select: **Record Expense** |
| 3 | Bot: Select category → You select: **Feed Purchase** |
| 4 | Bot: Enter number of bags → You type: **2** |
| 5 | Bot: Enter price per bag → You type: **2000** |
| 6 | Bot: Select payment method → You select: **M-PESA** |
| 7 | Bot: Select supplier → You select: **Best Feeds Ltd** |
| **Result** | ✓ Expense recorded: KSh 4,000<br>✓ Inventory updated: +140kg feed |

### 2.3 What Happens in the Database

**Table 1: financial_ledger**

| Date | Amount | Direction | Category | Payment | Contact |
|------|--------|-----------|----------|---------|---------|
| 2024-12-18 | 4,000 | OUT | FEED | M-PESA | Best Feeds Ltd |

**Table 2: inventory_items**

| Name | Type | Quantity | Unit | Cost/Unit |
|------|------|----------|------|-----------|
| Layer Mash | FEED | **145** | KG | 28.57 |

**Table 3: inventory_logs**

| Item Name | Quantity Change | Transaction Type | Linked To |
|-----------|----------------|------------------|-----------|
| Layer Mash | +140 | PURCHASE | financial_ledger (id) |

> **Note:** The system added 140kg to your existing 5kg, bringing total stock to 145kg. Cost per unit (KSh 28.57/kg) is automatically calculated from the total purchase.

---

## 3. Daily Operations: The Morning Routine

### 3.1 Recording Daily Activities

*Every morning, you collect eggs, feed your chickens, and check for any losses. The Daily Wizard guides you through this process in a logical sequence.*

#### Step 1: Egg Collection

| Interaction | Details |
|-------------|---------|
| **Action** | You: `/daily` |
| **Bot asks** | How many eggs did you collect today? |
| **You respond** | 180 |
| **Bot asks** | How many were broken or damaged? |
| **You respond** | 5 |
| **Bot calculates** | Good eggs: **175** (180 - 5) |

#### Step 2: Feed Usage

| Interaction | Details |
|-------------|---------|
| **Bot asks** | How many kilograms of feed did you use? |
| **You respond** | 2 |
| **Bot updates** | Feed stock: 145kg → 143kg |

#### Step 3: Mortality Check

| Interaction | Details |
|-------------|---------|
| **Bot asks** | Any bird losses today? |
| **You respond** | 1 |
| **Result** | ✓ Daily entry saved successfully! |

### 3.2 Database Updates

**Table: daily_entries**

| Date | Collected | Broken | Good | Feed (kg) | Deaths | Sold |
|------|-----------|--------|------|-----------|--------|------|
| 2024-12-18 | 180 | 5 | **175** | 2 | 1 | 0 |

**Table: inventory_items (Updated)**

| Item | Before | Change | After |
|------|--------|--------|-------|
| Eggs | 0 | +175 | **175** |
| Layer Mash (kg) | 145 | -2 | **143** |

---

## 4. Selling Eggs: Generating Income

### 4.1 Selling Loose Eggs

*Mama Mboga comes to buy 50 eggs at KSh 15 per egg.*

| Step | Action |
|------|--------|
| 1 | You: `/finance` → **Record Income** |
| 2 | Bot: Select product → You select: **Eggs (Loose)** |
| 3 | Bot: Current stock: **175 eggs available** |
| 4 | Bot: Enter quantity → You type: **50** |
| 5 | Bot: Enter price per unit → You type: **15** |
| 6 | Bot: Select customer → You select: **Mama Mboga** |
| 7 | Bot: Payment method → You select: **Cash** |
| **Result** | ✓ Sale recorded: KSh 750<br>✓ Stock updated: 175 → 125 eggs |

### 4.2 Selling in Crates

*A local hotel orders 3 crates (90 eggs) at KSh 400 per crate.*

| Step | Details |
|------|---------|
| **Action** | Select: **Eggs (Crates)** |
| **Bot calculates** | Available: **4 crates** (125 eggs ÷ 30 per crate) |
| **You enter** | Crates: **3**, Price per crate: **400** |
| **Result** | ✓ Income: KSh 1,200 (3 × 400)<br>✓ Stock: 125 → 35 eggs (3 crates = 90 eggs) |

### 4.3 Updated Database Records

**financial_ledger (New Entries)**

| Date | Amount | Direction | Category | Payment | Customer |
|------|--------|-----------|----------|---------|----------|
| 2024-12-18 | 750 | IN | EGG_SALE | Cash | Mama Mboga |
| 2024-12-18 | 1,200 | IN | EGG_SALE | M-PESA | Hotel Pride |

**daily_entries (Updated)**

| Date | Good Eggs | Eggs Sold | Income |
|------|-----------|-----------|--------|
| 2024-12-18 | 175 | **140** | **KSh 1,950** |

**inventory_items (Updated)**

| Item | Quantity |
|------|----------|
| Eggs | **35 pieces** |
| Layer Mash | **143 kg** |

---

## 5. Generating Reports: Understanding Your Business

### 5.1 Daily Report

**Command:** `/reports` → **Daily Report**

| Metric | Value |
|--------|-------|
| Eggs Collected | 180 |
| Eggs Broken | 5 |
| Good Eggs | **175** |
| Eggs Sold | 140 |
| Remaining Stock | 35 |
| Feed Used | 2 kg |
| Mortality | 1 bird |
| **Daily Income** | **KSh 1,950** |

### 5.2 Profit & Loss Statement

**Command:** `/reports` → **P&L Report (This Month)**

| Category | Amount (KSh) |
|----------|--------------|
| **INCOME** | |
| Egg Sales | 1,950 |
| **Total Income** | **1,950** |
| | |
| **EXPENSES** | |
| Feed Purchase | 4,000 |
| **Total Expenses** | **4,000** |
| | |
| **NET PROFIT/LOSS** | **-2,050** |

> **Note:** The negative profit shows you're in the early stages - you've made an initial investment in feed. As you continue selling eggs over the next weeks, you'll recover this cost and turn profitable.

---

## 6. Inventory Management: Keeping Track

### 6.1 Checking Current Stock

**Command:** `/inventory` → **View Stock**

| Item | Type | Current Stock | Status |
|------|------|---------------|--------|
| Eggs | PRODUCE | **35 pieces** | ✓ OK |
| Layer Mash | FEED | **143 kg** | ✓ OK |

### 6.2 Manual Stock Adjustment

If you discover a discrepancy (e.g., some feed was damaged by rain), you can manually adjust:

**Example:**
- Command: `/inventory` → **Adjust Stock**
- Select: **Layer Mash**
- Adjustment: **-10 kg**
- Reason: **Water damage**

**Result:** Stock updated: 143kg → 133kg, with audit log entry

---

## 7. Advanced Features

### 7.1 Low Stock Alerts

The system automatically monitors your inventory and sends alerts when stock runs low.

**Example Alert:**

> ⚠️ **Low Stock Alert**  
> Layer Mash is at 8kg (below 10kg threshold). Time to restock!

### 7.2 Performance Tracking

The bot tracks key performance metrics:

- **Egg production rate:** eggs per day per bird
- **Feed conversion ratio:** kg of feed per egg produced
- **Mortality rate trends:** tracking losses over time
- **Revenue per bird per day:** profitability per chicken

### 7.3 Demo Mode

Test new features without affecting your real data.

**Command:** `/demo` → **Switch to Demo Database**

All transactions in demo mode are completely isolated from your production data. Switch back anytime with `/demo` → **Production Mode**.

---

## 8. Complete Workflow Summary

### 8.1 Typical Day in Your Poultry Farm

| Time | Activity | Bot Command | Database Update |
|------|----------|-------------|-----------------|
| 6:00 AM | Collect eggs | `/daily` | daily_entries, inventory_items |
| 7:00 AM | Feed chickens | (via /daily wizard) | inventory_items (feed) |
| 8:00 AM | Customer buys eggs | `/finance` → Income | financial_ledger, daily_entries, inventory_items |
| 10:00 AM | Check inventory | `/inventory` | Read-only query |
| 2:00 PM | Buy more feed | `/finance` → Expense | financial_ledger, inventory_items, inventory_logs |
| 8:00 PM | Review daily report | `/reports` → Daily | Read-only query |

---

## 9. Contact Trust Score System

### 9.1 Overview

The trust score is a metric (0-100) that helps you track the reliability and quality of your business relationships with suppliers and customers.

### 9.2 How Trust Scores Work

**Default Score:** Every new contact starts with a trust score of **100**.

**Score Adjustments:**

#### For Suppliers:

| Event | Score Change | Example |
|-------|--------------|---------|
| Delivery delay (1-2 days) | -3 points | Supplier delivers feed 2 days late |
| Delivery delay (3+ days) | -5 points | Feed arrives a week late |
| Quality issues (damaged goods) | -10 points | 2 bags of feed are moldy |
| Wrong quantity delivered | -5 points | Ordered 5 bags, received only 4 |
| Price increase without notice | -3 points | Suddenly charges KSh 2,500 instead of KSh 2,000 |
| Consistent good service (monthly) | +2 points | On-time, quality deliveries all month |
| Quick emergency response | +5 points | Delivers urgently when you run out |

#### For Customers:

| Event | Score Change | Example |
|-------|--------------|---------|
| Late payment (1-3 days) | -3 points | Promised to pay Friday, pays Monday |
| Late payment (4-7 days) | -5 points | Payment delayed a week |
| Bounced payment/check | -15 points | M-PESA payment fails or check bounces |
| Dispute/complaint | -10 points | Customer claims eggs were bad |
| Returns excessive product | -8 points | Returns 20% of eggs multiple times |
| Consistent purchases (monthly) | +2 points | Reliable weekly buyer |
| Prompt payment | +1 point | Always pays on delivery |
| Referral brings new customer | +5 points | Recommends your farm to others |

### 9.3 Trust Score Thresholds

| Score Range | Status | Color Code | Meaning |
|-------------|--------|------------|---------|
| 90-100 | Excellent | 🟢 Green | Highly reliable, preferred partner |
| 70-89 | Good | 🟡 Yellow | Generally reliable, minor issues |
| 50-69 | Fair | 🟠 Orange | Some concerns, monitor closely |
| 30-49 | Poor | 🔴 Red | Frequent problems, high risk |
| 0-29 | Critical | ⚫ Black | Severe issues, consider blocking |

### 9.4 Practical Applications

#### 1. Automatic Alerts

```
⚠️ Warning: You're about to transact with "Late Pay Farms"
Trust Score: 45 (Poor)
History: 3 late payments, 1 bounced check
Recommendation: Request advance payment
```

#### 2. Credit Decisions

- **Trust Score > 80:** Extend up to 30 days credit
- **Trust Score 60-79:** Offer 7-14 days credit
- **Trust Score < 60:** Cash only

#### 3. Priority Rankings

When viewing contacts, the system can sort by trust score:

```
Top Suppliers:
1. Best Feeds Ltd (Trust: 98) ⭐
2. Quality Mash Co (Trust: 95) ⭐
3. Farm Supplies Inc (Trust: 87)
4. Budget Feed Store (Trust: 52) ⚠️
```

#### 4. Transaction Blocking

Set automatic rules:
- Block new transactions with trust score < 30
- Require manager approval for trust score < 50
- Flag transactions with declining trust trends

### 9.5 Implementation Recommendations

#### Phase 1: Manual Tracking
1. Add trust score field to contact display
2. Allow manual adjustments via `/contacts` → **Edit Contact** → **Adjust Trust Score**
3. Require reason notes for adjustments

#### Phase 2: Semi-Automatic
1. Bot prompts after transactions: "Rate this transaction (Good/Fair/Poor)"
2. System suggests score adjustments based on rating
3. User confirms or modifies the adjustment

#### Phase 3: Fully Automatic
1. Track payment dates vs. due dates automatically
2. Monitor product quality through return rates
3. Calculate average delivery times
4. Auto-adjust scores based on rules engine

### 9.6 Example Workflow

**Scenario:** Supplier delivers late

```
Day 1: Order placed
Day 4: Expected delivery (not arrived)
Day 6: Feed finally arrives

Bot: "Best Feeds Ltd delivered 2 days late. Adjust trust score?"
Options:
- Yes, apply -3 points (Score: 100 → 97)
- No, delivery delay was reasonable
- Add custom adjustment with note

User selects: "Yes, apply -3 points"
Bot: "Trust score updated. Note: 2-day delivery delay on 2024-12-20"
```

### 9.7 Reporting

#### Trust Score Report
**Command:** `/contacts` → **Trust Report**

```
Trust Score Summary:
━━━━━━━━━━━━━━━━━━━━━
Suppliers:
  Excellent (90+): 3 contacts
  Good (70-89): 2 contacts
  Fair (50-69): 1 contact
  Poor (30-49): 0 contacts

Customers:
  Excellent (90+): 8 contacts
  Good (70-89): 5 contacts
  Fair (50-69): 2 contacts
  Poor (30-49): 1 contact ⚠️

Recommended Actions:
• Review "Cash Late Customer" (Trust: 42)
• Consider blocking "Unreliable Buyer" (Trust: 28)
```

### 9.8 Best Practices

1. **Be Consistent:** Apply the same standards to all contacts
2. **Document Reasons:** Always add notes when adjusting scores
3. **Review Regularly:** Monthly review of all contacts below 70
4. **Balance Scores:** Good behavior should restore trust over time
5. **Communication:** Share concerns with low-trust contacts before blocking
6. **Second Chances:** Allow trust rebuilding through consistent good behavior

---

## 10. Conclusion

The Avionyx Poultry Management System provides a complete, integrated solution for managing every aspect of your poultry farm. From purchasing supplies to selling products to analyzing performance, every transaction is tracked, every metric is measured, and every decision is data-driven.

### Key Benefits:

- ✓ Complete financial tracking (income and expenses)
- ✓ Real-time inventory management
- ✓ Automated daily operations logging
- ✓ Comprehensive reporting and analytics
- ✓ Contact management with trust scoring
- ✓ Proactive alerts for low stock and anomalies
- ✓ Demo mode for testing and training

### Getting Started:

1. Add your suppliers and customers (`/contacts`)
2. Record your initial inventory (`/inventory`)
3. Start your daily routine (`/daily`)
4. Track all financial transactions (`/finance`)
5. Review reports regularly (`/reports`)
6. Monitor trust scores monthly

---

*For support and more information, contact your system administrator.*

**Version:** 1.0  
**Last Updated:** December 2024  
**System:** Avionyx Poultry Management Bot
