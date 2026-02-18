# PLM BOM Import Tool - Documentation

## Overview

The **PLM BOM Import Tool** is a Frappe/ERPNext doctype that facilitates importing Product Lifecycle Management (PLM) files to create Items and Bill of Materials (BOM) structures in the system.

---

## Features

1. **Import Items from PLM Files** - Parse PLM files and create item masters
2. **Create BOM Structures** - Generate BOM Creator documents from PLM hierarchies
3. **Smart UI Controls** - Context-aware buttons and validations
4. **Navigation Helpers** - Quick access to created BOM Creators and BOMs
5. **Detailed Logging** - Comprehensive logs for both item and BOM creation processes

---

## How It Works

### File Structure

- **plm_bom_import_tool.js** - Client-side form controller (this documentation)
- **plm_bom_import_tool.py** - Server-side Python controller with business logic
- **plm_bom_import_tool.json** - DocType definition and field metadata

---

## JavaScript Code Walkthrough

### 1. Form Event: `refresh(frm)`

**Trigger:** When the form loads or refreshes

**What it does:**
- Shows/hides Item Create and BOM Create buttons based on context
- Adds "View BOM Creator" button if applicable
- Adds "View BOM" button if a BOM has been created

**Code Flow:**
```javascript
refresh(frm) {
    toggle_create_buttons(frm);              // Step 1: Toggle UI buttons
    add_bom_creator_button_from_parent(frm); // Step 2: Add BOM Creator button
    add_view_bom_button_from_log(frm);       // Step 3: Add View BOM button
}
```

---

### 2. Form Event: `bom_parent_item(frm)`

**Trigger:** When the `bom_parent_item` field changes

**What it does:**
- Hides Item/BOM Create buttons when a parent item is selected
- Shows them when the field is cleared

**Why:** If a parent item is already selected, items presumably exist, so import buttons aren't needed.

---

### 3. Form Event: `item_create(frm)`

**Trigger:** When user clicks the "Item Create" button

**Workflow:**

```
1. Validate PLM file is attached
   ↓
2. Show error if missing → STOP
   ↓
3. Call backend method: import_items()
   ↓
4. Freeze UI with "Creating items from PLM file..." message
   ↓
5. Receive response with log and summary
   ↓
6. Update item_creation_log field
   ↓
7. Show summary popup to user
   ↓
8. Refresh log field display
```

**Backend Method Called:**
```
plm_bom.plm_bom.doctype.plm_bom_import_tool.plm_bom_import_tool.import_items
```

**Response Structure:**
```javascript
{
    log: "Detailed creation log text...",
    summary: "Created 15 items successfully"
}
```

---

### 4. Form Event: `bom_create(frm)`

**Trigger:** When user clicks the "BOM Create" button

**Workflow:**

```
1. Validate PLM file is attached
   ↓
2. Show error if missing → STOP
   ↓
3. Call backend method: import_bom_creator()
   ↓
4. Freeze UI with "Creating BOM Creator from PLM file..." message
   ↓
5. Receive response with log, summary, and bom_creator name
   ↓
6. Update bom_creation_log field
   ↓
7. Show summary popup
   ↓
8. Add "View BOM Creator" button
   ↓
9. Add "View BOM" button
   ↓
10. Refresh log field display
```

**Backend Method Called:**
```
plm_bom.plm_bom.doctype.plm_bom_import_tool.plm_bom_import_tool.import_bom_creator
```

**Response Structure:**
```javascript
{
    log: "Detailed BOM creation log...",
    summary: "BOM Creator created successfully",
    bom_creator: "ITEM-001" // Name of created BOM Creator
}
```

---

## Helper Functions

### `toggle_create_buttons(frm)`

**Purpose:** Show or hide Item Create and BOM Create buttons

**Logic:**
- **IF** `bom_parent_item` is set:
  - Remove Item Create button
  - Remove BOM Create button
  - Hide both button fields
- **ELSE:**
  - Show both button fields

**Why this matters:** When working with an existing parent item, we don't need to import new items from PLM files.

---

### `add_bom_creator_button_from_log(frm)`

**Purpose:** Extract BOM Creator name from the log text and add a navigation button

**How it works:**
1. Check if `bom_creation_log` field has content
2. Use regex to find "BOM Creator [NAME]" pattern
3. Extract the name
4. Call `add_bom_creator_button()` with the extracted name

**Regex Pattern:**
```javascript
/BOM Creator\s+([^\.\n]+)/
```
- `BOM Creator` - Literal text
- `\s+` - One or more whitespace characters
- `([^\.\n]+)` - Capture everything until a period or newline

**Example Log:**
```
Created BOM Creator ITEM-001 successfully.
Items: 25, Levels: 3
```
**Extracted:** `ITEM-001`

---

### `add_bom_creator_button_from_parent(frm)`

**Purpose:** Add BOM Creator button using the parent item field

**Priority Logic:**
1. **First Priority:** Use `bom_parent_item` field if available
2. **Fallback:** Parse the log using `add_bom_creator_button_from_log()`

**Why:** The parent item field is more reliable than text parsing.

---

### `add_view_bom_button_from_log(frm)`

**Purpose:** Similar to `add_bom_creator_button_from_log()` but for the "View BOM" button

**What it does:**
- Parses log to find BOM Creator name
- Adds "View BOM" button that navigates to the final BOM document

---

### `add_bom_creator_button(frm, bomCreatorName)`

**Purpose:** Create a button that navigates to the BOM Creator form

**Parameters:**
- `frm` - Form object
- `bomCreatorName` - Name/ID of the BOM Creator document

**What it does:**
```javascript
frm.add_custom_button(__("View BOM Creator"), () => {
    frappe.set_route("Form", "BOM Creator", bomCreatorName);
});
```

**User Experience:**
- Adds button to toolbar
- Clicking it opens the BOM Creator form in view/edit mode

---

### `add_view_bom_button(frm, bomCreatorName)`

**Purpose:** Create a button that fetches and navigates to the final BOM document

**Parameters:**
- `frm` - Form object
- `bomCreatorName` - Name/ID of the BOM Creator document

**Workflow:**

```
User clicks "View BOM" button
   ↓
Call backend: get_bom_for_bom_creator()
   ↓
Backend searches for BOM linked to this BOM Creator
   ↓
IF BOM found:
   → Navigate to BOM form
ELSE:
   → Show message: "BOM not found yet. Please wait and try again."
```

**Why this complexity?**
The BOM Creator might exist, but the final BOM document may not be generated yet (could be async process).

**Backend Method Called:**
```
plm_bom.plm_bom.doctype.plm_bom_import_tool.plm_bom_import_tool.get_bom_for_bom_creator
```

---

## User Workflows

### Workflow 1: Import Items from PLM File

```
1. User creates new PLM BOM Import Tool document
2. User attaches PLM file to plm_file field
3. User clicks "Item Create" button
4. System parses PLM file and creates items
5. Results shown in item_creation_log field
6. Summary popup displays success/failure count
```

### Workflow 2: Create BOM from PLM File

```
1. User creates new PLM BOM Import Tool document
2. User attaches PLM file to plm_file field
3. User clicks "BOM Create" button
4. System creates BOM Creator document
5. Results shown in bom_creation_log field
6. "View BOM Creator" button appears
7. "View BOM" button appears
8. User can navigate to BOM Creator or final BOM
```

### Workflow 3: Working with Existing Parent Item

```
1. User creates new PLM BOM Import Tool document
2. User sets bom_parent_item field
3. Item/BOM Create buttons are hidden (items already exist)
4. "View BOM Creator" button appears using parent item name
5. User can view/edit the BOM Creator
```

---

## Key Technical Concepts

### 1. Form Freezing
```javascript
freeze: true,
freeze_message: __("Creating items from PLM file...")
```
- Prevents user interaction during long operations
- Shows loading message
- Provides better UX

### 2. Frappe Translation
```javascript
__("Please attach a PLM file before creating items.")
```
- All user-facing strings wrapped in `__()`
- Enables multi-language support
- Follows Frappe best practices

### 3. Promise-based API Calls
```javascript
frappe.call({ ... }).then((response) => { ... });
```
- Asynchronous operations
- Non-blocking UI
- Clean error handling

### 4. Dynamic Button Management
```javascript
frm.add_custom_button()      // Add button
frm.remove_custom_button()   // Remove button
frm.toggle_display()         // Show/hide field
```
- Context-aware UI
- Reduces clutter
- Improves user experience

---

## Data Flow Diagram

```
┌─────────────────┐
│   User Action   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validation     │ ─────► Error? ──► Show Message ──► Stop
│  (PLM file?)    │
└────────┬────────┘
         │ ✓
         ▼
┌─────────────────┐
│  Backend Call   │
│  (Python)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parse PLM File │
│  Create Records │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Return Result  │
│  (log, summary) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Update UI      │
│  - Log field    │
│  - Buttons      │
│  - Messages     │
└─────────────────┘
```

---

## Field Reference

| Field Name | Type | Purpose |
|------------|------|---------|
| `plm_file` | Attach | PLM file to import |
| `bom_parent_item` | Link | Existing parent item (optional) |
| `item_creation_log` | Text | Log of item creation process |
| `bom_creation_log` | Text | Log of BOM creation process |
| `item_create` | Button | Trigger item import |
| `bom_create` | Button | Trigger BOM creation |

---

## Common Issues & Solutions

### Issue: "Please attach a PLM file before creating items"
**Cause:** User clicked Item Create or BOM Create without attaching a PLM file  
**Solution:** Attach a valid PLM file to the `plm_file` field

### Issue: "BOM not found yet. Please wait and try again"
**Cause:** BOM Creator exists but final BOM document hasn't been generated yet  
**Solution:** Wait for BOM generation to complete, then click "View BOM" again

### Issue: Create buttons are hidden
**Cause:** `bom_parent_item` field is set  
**Solution:** This is expected behavior - clear the field if you want to import from PLM file

---

## Development Notes

### Adding New Buttons
To add a new custom button:
```javascript
frm.add_custom_button(__("Button Label"), () => {
    // Button click handler
    frappe.msgprint("Button clicked!");
});
```

### Calling Backend Methods
```javascript
frappe.call({
    method: "path.to.python.method",
    args: {
        param1: value1,
        param2: value2
    },
    freeze: true,
    freeze_message: __("Processing...")
}).then((response) => {
    console.log(response.message);
});
```

### Regex Tips for Log Parsing
Current pattern: `/BOM Creator\s+([^\.\n]+)/`

To modify:
- Change "BOM Creator" to your search text
- `\s+` matches spaces/tabs
- `([^\.]+)` captures until first period
- `([^\n]+)` captures until newline
- Use `match[1]` to get captured group

---

## Best Practices Followed

✅ **Validation before API calls** - Check required fields first  
✅ **User feedback** - Show freeze messages, summaries, and errors  
✅ **Graceful fallbacks** - Try multiple methods to find data  
✅ **Clean code** - Helper functions for reusability  
✅ **Comprehensive logging** - Detailed logs for troubleshooting  
✅ **Translation support** - All strings wrapped in `__()`  
✅ **Context-aware UI** - Buttons appear/disappear based on state  

---

## Copyright

Copyright (c) 2026, Vivek Choudhary and contributors  
For license information, please see license.txt

---

## Version History

- **v1.0** - Initial implementation with item and BOM creation features

---

*This documentation is maintained alongside the code. Last updated: Feb 2026*
