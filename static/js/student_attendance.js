/**
 * Student Geolocation Attendance Handler
 * Captures GPS coordinates via navigator.geolocation and posts to Flask backend
 * for pure Python Haversine geofence verification.
 */
document.addEventListener("DOMContentLoaded", function () {
    const markBtn = document.getElementById("markAttendanceBtn");
    const feedbackBox = document.getElementById("geoFeedback");
    const feedbackTitle = document.getElementById("feedbackTitle");
    const feedbackMessage = document.getElementById("feedbackMessage");
    const feedbackCoords = document.getElementById("feedbackCoords");
    const todayStatusBadge = document.getElementById("todayStatusBadge");
    const historyTableBody = document.getElementById("historyTableBody");
    const noRecordsRow = document.getElementById("noRecordsRow");

    if (!markBtn) return;

    const postUrl = markBtn.getAttribute("data-url");

    markBtn.addEventListener("click", function () {
        if (!navigator.geolocation) {
            showFeedback(
                "error",
                "⚠️ Geolocation Not Supported",
                "Your web browser does not support HTML5 Geolocation. Please use an updated modern browser.",
                ""
            );
            return;
        }

        // Set UI loading state
        markBtn.disabled = true;
        markBtn.textContent = "📡 Acquiring GPS Location...";
        showFeedback(
            "loading",
            "🛰️ Locating Device...",
            "Requesting your current high-accuracy coordinates from browser GPS sensors...",
            ""
        );

        navigator.geolocation.getCurrentPosition(
            // Success callback
            function (position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const accuracy = position.coords.accuracy ? Math.round(position.coords.accuracy) : null;

                markBtn.textContent = "🔄 Verifying Geofence...";
                showFeedback(
                    "loading",
                    "🔄 Verifying With Campus Geofence...",
                    "Comparing your coordinates against the college center point using the Haversine formula...",
                    `Detected GPS: ${lat.toFixed(6)}, ${lon.toFixed(6)}${accuracy ? ` (Accuracy: ~${accuracy}m)` : ""}`
                );

                // Send coordinates to Flask backend
                fetch(postUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({
                        latitude: lat,
                        longitude: lon
                    })
                })
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    if (data.success) {
                        // Mark as Present
                        markBtn.textContent = "✓ Attendance Marked";
                        markBtn.className = "btn btn-success btn-lg";
                        markBtn.disabled = true;

                        showFeedback(
                            "success",
                            "✅ Attendance Verified & Recorded!",
                            data.message,
                            `GPS: ${lat.toFixed(6)}, ${lon.toFixed(6)} &bull; Calculated Distance: ${data.distance}m (Allowed Radius: ${data.radius}m)`
                        );

                        // Update today's status badge
                        if (todayStatusBadge) {
                            todayStatusBadge.textContent = "✓ Present";
                            todayStatusBadge.className = "badge badge-present";
                        }

                        // Update or insert today's entry in history table
                        if (noRecordsRow) {
                            noRecordsRow.remove();
                        }

                        const existingTodayRow = document.getElementById(`row-${data.date}`);
                        if (!existingTodayRow && historyTableBody) {
                            const newRow = document.createElement("tr");
                            newRow.id = `row-${data.date}`;
                            newRow.innerHTML = `
                                <td>1</td>
                                <td><strong>${data.date}</strong></td>
                                <td><span class="badge badge-present">✓ Present</span></td>
                            `;
                            historyTableBody.insertBefore(newRow, historyTableBody.firstChild);
                        }
                    } else {
                        // Outside geofence or rejected
                        markBtn.textContent = "📍 Retry Marking Attendance";
                        markBtn.disabled = false;

                        showFeedback(
                            "error",
                            "❌ Geofence Verification Failed",
                            data.message,
                            `GPS: ${lat.toFixed(6)}, ${lon.toFixed(6)} &bull; Calculated Distance: ${data.distance}m (Allowed Radius: ${data.radius}m)`
                        );
                    }
                })
                .catch(function (err) {
                    markBtn.textContent = "📍 Retry Marking Attendance";
                    markBtn.disabled = false;

                    showFeedback(
                        "error",
                        "Network / Server Error",
                        "Could not communicate with the server: " + err.message,
                        ""
                    );
                });
            },
            // Error callback
            function (error) {
                markBtn.textContent = "📍 Retry Marking Attendance";
                markBtn.disabled = false;

                let errMsg = "Unable to retrieve your location.";
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errMsg = "Location access was denied. Please allow location permissions in your browser or device settings to verify attendance.";
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errMsg = "Location information is unavailable. Ensure your device GPS/location service is toggled ON.";
                        break;
                    case error.TIMEOUT:
                        errMsg = "The request to get your location timed out. Please try again in an area with clear reception.";
                        break;
                    default:
                        errMsg = error.message;
                }

                showFeedback("error", "⚠️ Geolocation Error", errMsg, "");
            },
            // Options: high accuracy, 15s timeout, fresh location
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            }
        );
    });

    function showFeedback(type, title, message, coords) {
        if (!feedbackBox) return;
        feedbackBox.className = `geo-result ${type}`;
        if (feedbackTitle) feedbackTitle.textContent = title;
        if (feedbackMessage) feedbackMessage.innerHTML = message;
        if (feedbackCoords) feedbackCoords.innerHTML = coords || "";
    }
});
