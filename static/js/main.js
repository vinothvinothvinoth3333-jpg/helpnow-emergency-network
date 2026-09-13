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