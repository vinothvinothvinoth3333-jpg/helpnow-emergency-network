function getLocation() {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function (position) {
            const latitude = document.getElementById("latitude");
            const longitude = document.getElementById("longitude");
            const locationResult = document.getElementById("locationResult");
            const mapLink = document.getElementById("mapLink");
            const latitudeValue = position.coords.latitude.toFixed(6);
            const longitudeValue = position.coords.longitude.toFixed(6);

            if (latitude) {
                latitude.value = latitudeValue;
            }
            if (longitude) {
                longitude.value = longitudeValue;
            }
            if (locationResult) {
                locationResult.hidden = false;
                locationResult.textContent = `Location found: ${latitudeValue}, ${longitudeValue}`;
            }
            if (mapLink) {
                mapLink.hidden = false;
                mapLink.href = `https://www.google.com/maps/search/?api=1&query=${latitudeValue},${longitudeValue}`;
            }
        },
        function () {
            alert("Unable to get your location. Please allow location permission.");
        }
    );
}

function startLiveLocation(reportId) {
    if (!navigator.geolocation) {
        return;
    }

    const status = document.getElementById("liveLocationStatus");
    const watchId = navigator.geolocation.watchPosition(
        function (position) {
            const payload = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            };

            fetch(`/api/reports/${reportId}/location`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }).then(function (response) {
                if (!response.ok) {
                    throw new Error("Location update failed");
                }
                if (status) {
                    status.textContent = "Live location is being shared with the HelpNow owner.";
                }
            }).catch(function () {
                if (status) {
                    status.textContent = "Live location could not be updated. Check your connection.";
                }
            });
        },
        function () {
            if (status) {
                status.textContent = "Location permission is required for live sharing.";
                status.classList.add("error");
                status.classList.remove("success");
            }
        },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
    );

    const stopButton = document.getElementById("stopLiveLocation");
    if (stopButton) {
        stopButton.addEventListener("click", function () {
            navigator.geolocation.clearWatch(watchId);
            fetch(`/api/reports/${reportId}/location/stop`, { method: "POST" });
            stopButton.disabled = true;
            if (status) {
                status.textContent = "Live location sharing stopped.";
            }
        });
    }
}

function refreshOwnerLocations() {
    fetch("/api/owner/reports")
        .then(function (response) { return response.json(); })
        .then(function (data) {
            data.reports.forEach(function (report) {
                if (report.latitude === null || report.longitude === null) {
                    return;
                }
                const coordinates = `${report.latitude.toFixed(6)}, ${report.longitude.toFixed(6)}`;
                const location = document.querySelector(`[data-location="${report.id}"]`);
                const details = document.querySelector(`[data-location-details="${report.id}"]`);
                const mapLink = document.querySelector(`[data-map-link="${report.id}"]`);
                const liveBadge = document.querySelector(`[data-live="${report.id}"]`);
                if (!report.live_location && liveBadge) {
                    liveBadge.remove();
                }
                if (details) {
                    const liveLabel = report.live_location ? `<span class="live-badge" data-live="${report.id}">LIVE</span>` : "";
                    details.outerHTML = `<p class="location-details"><span data-location="${report.id}">${coordinates}</span>${liveLabel}<br><a data-map-link="${report.id}" href="https://www.google.com/maps/search/?api=1&query=${report.latitude},${report.longitude}" target="_blank" rel="noopener">View user location on map</a></p>`;
                } else if (location) {
                    location.textContent = coordinates;
                    if (mapLink) {
                        mapLink.href = `https://www.google.com/maps/search/?api=1&query=${report.latitude},${report.longitude}`;
                    }
                }
            });
        })
        .catch(function () {});
}

document.addEventListener("DOMContentLoaded", function () {
    const submittedReport = new URLSearchParams(window.location.search).get("submitted");
    const isLive = new URLSearchParams(window.location.search).get("live") === "1";
    if (submittedReport && isLive) {
        startLiveLocation(submittedReport);
    }
    if (document.querySelector("[data-location], [data-location-details]")) {
        refreshOwnerLocations();
        window.setInterval(refreshOwnerLocations, 5000);
    }
});