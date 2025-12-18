# Changelog

## [3.0.0] - 2025-12-18
### Added
- **"Nano Banana" Business Intelligence Module**:
    - **Financials**: Detailed P&L with net margin calculation and category breakdown.
    - **Production**: Advanced efficiency metrics including Feed per Egg (g/egg) and laying rates.
    - **Inventory Forecasting**: Burn rate estimates for feed and stock depletion projections (days remaining).
- **Health & Vaccination Tracking**:
    - Decoupled "Birds Vaccinated" from "Stock Used" to support bulk medication units (bottles/vials).
    - Intelligent prompt logic based on vaccine unit types (doses vs bulk).
- **Customer CRM**: Ability to track specific customers for sales and add new customers on-the-fly.
- **Validation Suite**: Prevent zero or negative quantity inputs across all financial and inventory modules.
- **Flock Management**: Enforced unique batch names (case-insensitive) for better tracking.

### Changed
- Refined **Report** menu with a cleaner, high-fidelity UI.
- Optimized **Bird Purchase** flow: Auto-selection of livestock types and streamlined flock creation.
- Enhanced **Flock Information**: Displaying detailed gender breakdown (Hens/Roosters) in selection lists.

### Fixed
- Fixed `AttributeError` in cleanup jobs.
- Resolved database session leakage issues in report generation.
- Corrected unit conversion logic in vaccination recording.

## [2.0.0] - 2024-12-10
### Added
- Finance module with Expense/Income tracking.
- Inventory module for Feed and Medication.
- Alembic migration support.
- Production Alerting system.

## [1.0.0] - 2024-11-20
### Added
- Initial release with basic Egg and Feed tracking.
- Daily Wizard for 1-minute daily entries.
