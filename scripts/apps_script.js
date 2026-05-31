// MyFolioPulse — Google Apps Script
// Paste this entire script into the Apps Script editor and deploy as a Web App.

const SHEET_NAME = "Sheet1";
const SECRET_TOKEN = "mfp_2026_secret"; // Change this to something unique before going live

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);

    // Basic token check (security layer)
    if (payload.token !== SECRET_TOKEN) {
      return jsonResponse({ status: "error", message: "Unauthorised" });
    }

    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);

    // Check for duplicate email
    const data = sheet.getDataRange().getValues();
    for (let i = 1; i < data.length; i++) {
      if (data[i][2] === payload.email) {
        return jsonResponse({ status: "error", message: "Email already registered" });
      }
    }

    // Generate a UUID for this user
    const userId = generateUUID();
    const dashboardUrl = `https://muralmu.github.io/my-folio-pulse/users/${userId}.html`;

    // Append new row
    sheet.appendRow([
      userId,
      payload.name,
      payload.email,
      payload.timezone,
      JSON.stringify(payload.funds),
      new Date().toISOString(),
      "true",
      dashboardUrl
    ]);

    return jsonResponse({
      status: "ok",
      userId: userId,
      dashboardUrl: dashboardUrl
    });

  } catch (err) {
    return jsonResponse({ status: "error", message: err.toString() });
  }
}

// Handle preflight CORS requests
function doGet(e) {
  return jsonResponse({ status: "ok", message: "MyFolioPulse API is running" });
}

function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
