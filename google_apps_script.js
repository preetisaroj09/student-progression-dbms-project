/**
 * ============================================================================
 * Student Academic Progression and Portfolio Management System
 * Google Apps Script Webhook Engine
 * ============================================================================
 * 
 * Supports all 8 ERP relational tabs:
 * 1. achievement_categories
 * 2. students (with 8 core columns: ID, Roll No, Name, Email, Batch, Status, Phone, Department)
 * 3. school_records (Secondary 10th & Higher Secondary 12th details)
 * 4. semesters (or semester_results)
 * 5. subjects (theory & lab course marks)
 * 6. drop_years (academic gap years)
 * 7. achievements (seminars, workshops, hackathons, sports, co-curricular)
 */

function doPost(e) {
  try {
    var rawData = e.postData.contents;
    var data = JSON.parse(rawData);
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    // Table export priority list
    var tableOrder = [
      "achievement_categories",
      "students",
      "school_records",
      "semesters",
      "subjects",
      "semester_results",
      "drop_years",
      "achievements",
      "Students",
      "Semesters",
      "Subject Marks",
      "Drop Years",
      "Seminars",
      "Activities"
    ];

    for (var i = 0; i < tableOrder.length; i++) {
      var sheetName = tableOrder[i];
      if (data[sheetName] && data[sheetName].length > 0) {
        var sheet = ss.getSheetByName(sheetName);
        if (!sheet) {
          sheet = ss.insertSheet(sheetName);
        }
        
        // Clear previous content
        sheet.clear();

        var rows = data[sheetName];
        var numRows = rows.length;
        var numCols = rows[0].length;

        // Write table values in batch
        var range = sheet.getRange(1, 1, numRows, numCols);
        range.setValues(rows);

        // Format Header Row: Navy Blue Background (#0f172a), White Bold Font
        var headerRange = sheet.getRange(1, 1, 1, numCols);
        headerRange.setBackground("#0f172a");
        headerRange.setFontColor("#ffffff");
        headerRange.setFontWeight("bold");
        headerRange.setFontSize(10);
        headerRange.setHorizontalAlignment("center");
        sheet.setFrozenRows(1);

        // Format Data Rows
        if (numRows > 1) {
          var dataRange = sheet.getRange(2, 1, numRows - 1, numCols);
          dataRange.setFontSize(9);
          dataRange.setVerticalAlignment("middle");
        }
      }
    }

    // Remove default blank "Sheet1" once our tabs are created
    var defaultSheet = ss.getSheetByName("Sheet1");
    if (defaultSheet && ss.getSheets().length > 1) {
      try {
        ss.deleteSheet(defaultSheet);
      } catch (err) {}
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Google Sheets synchronized successfully!",
      spreadsheet_url: ss.getUrl()
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// 2. Health check endpoint (also returns the direct spreadsheet link)
function doGet(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  return ContentService.createTextOutput(JSON.stringify({
    status: "active",
    system: "Student Academic Progression DBMS Sync Webhook",
    spreadsheet_url: ss.getUrl(),
    spreadsheet_id: ss.getId(),
    timestamp: new Date().toISOString()
  })).setMimeType(ContentService.MimeType.JSON);
}

// 3. Custom Menu inside Google Sheets for Examiners
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("🎓 Academic Progression DBMS")
    .addItem("📊 Initialize All 8 DBMS Tabs", "initializeTabs")
    .addItem("📐 Auto-Fit All Column Widths", "autoFitAllColumns")
    .addItem("🧹 Clear All Tables", "clearAllTabs")
    .addSeparator()
    .addItem("ℹ️ About DBMS Sync", "showAbout")
    .addToUi();
}

function autoFitAllColumns() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var sheet = sheets[i];
    var lastCol = sheet.getLastColumn();
    for (var c = 1; c <= lastCol; c++) {
      sheet.autoResizeColumn(c);
    }
  }
  SpreadsheetApp.getUi().alert("Columns resized to fit content perfectly!");
}

function initializeTabs() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tabs = [
    "achievement_categories",
    "students",
    "school_records",
    "semesters",
    "subjects",
    "semester_results",
    "drop_years",
    "achievements"
  ];
  for (var i = 0; i < tabs.length; i++) {
    if (!ss.getSheetByName(tabs[i])) {
      ss.insertSheet(tabs[i]);
    }
  }
  SpreadsheetApp.getUi().alert("All 8 DBMS tabs initialized and styled!");
}

function clearAllTabs() {
  var ui = SpreadsheetApp.getUi();
  var res = ui.alert("Warning", "Are you sure you want to clear all data in the DBMS tabs?", ui.ButtonSet.YES_NO);
  if (res == ui.Button.YES) {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheets = ss.getSheets();
    for (var i = 0; i < sheets.length; i++) {
      sheets[i].clear();
    }
    ui.alert("All tabs cleared.");
  }
}

function showAbout() {
  SpreadsheetApp.getUi().alert(
    "Student Academic Progression DBMS",
    "This spreadsheet is synchronized automatically via HTTP Webhooks from your Flask & SQLAlchemy DBMS application.\n\nTabs:\n- achievement_categories\n- students\n- school_records\n- semesters\n- subjects\n- semester_results\n- drop_years\n- achievements",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
