function getLocation() {

    if (navigator.geolocation) {

        navigator.geolocation.getCurrentPosition(
            function(position) {

                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                document.getElementById("latitude").value = latitude;
                document.getElementById("longitude").value = longitude;

            },
            function(error) {

                alert("Unable to get your location.");

            }
        );

    } else {

        alert("Geolocation is not supported by your browser.");

    }
}