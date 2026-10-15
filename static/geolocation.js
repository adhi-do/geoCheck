document.getElementById('getLocationBtn').addEventListener('click', function() {
    const btn = this;
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser");
        return;
    }

    btn.textContent = "Getting Location...";
    btn.disabled = true;

    navigator.geolocation.getCurrentPosition(
        function(position) {
            document.querySelector('input[name="latitude"]').value = position.coords.latitude;
            document.querySelector('input[name="longitude"]').value = position.coords.longitude;
            btn.textContent = "Get Current GPS Location";
            btn.disabled = false;
        },
        function(error) {
            alert("Unable to retrieve your location: " + error.message);
            btn.textContent = "Get Current GPS Location";
            btn.disabled = false;
        },
        { enableHighAccuracy: true,  maximumAge: 0 }
        // { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
});
