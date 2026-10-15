import math

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the Earth
    specified in decimal degrees (latitude, longitude) using the pure Python
    Haversine formula.

    :param lat1: Latitude of point 1 in decimal degrees
    :param lon1: Longitude of point 1 in decimal degrees
    :param lat2: Latitude of point 2 in decimal degrees
    :param lon2: Longitude of point 2 in decimal degrees
    :return: Distance between point 1 and point 2 in meters
    """
    # Earth radius in meters (mean radius)
    EARTH_RADIUS_METERS = 6371000.0

    # Convert decimal degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )

    # Great-circle angular distance in radians using atan2 for numerical stability
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    # Calculate distance in meters
    distance = EARTH_RADIUS_METERS * c
    return distance
