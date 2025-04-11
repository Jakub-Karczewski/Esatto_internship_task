from typing import List, Dict, Optional
from pydantic import BaseModel

# Define models matching your JSON structure

from typing import List, Dict, Optional
from pydantic import BaseModel
import requests


class Station(BaseModel):
    distance: float
    latitude: float
    longitude: float
    useCount: int
    id: str
    name: str
    quality: int
    contribution: float


class Hour(BaseModel):
    datetime: str
    datetimeEpoch: int
    temp: float
    feelslike: float
    humidity: float
    dew: float
    precip: float
    precipprob: float
    snow: float
    snowdepth: float
    preciptype: Optional[List[str]] = None
    windgust: Optional[float] = None
    windspeed: float
    winddir: float
    pressure: float
    visibility: float
    cloudcover: float
    solarradiation: Optional[float] = None
    solarenergy: Optional[float] = None
    uvindex: Optional[int] = None
    conditions: str
    icon: str
    stations: List[str]
    source: str


class Normal(BaseModel):
    tempmax: List[float]
    tempmin: List[float]
    feelslike: List[float]
    precip: List[float]
    humidity: List[float]
    snowdepth: List[Optional[float]]  # Some platforms may yield None
    windspeed: List[float]
    windgust: List[float]
    winddir: List[float]
    cloudcover: List[float]


class Day(BaseModel):
    datetime: str
    datetimeEpoch: int
    tempmax: float
    tempmin: float
    temp: float
    feelslikemax: float
    feelslikemin: float
    feelslike: float
    dew: float
    humidity: float
    precip: float
    precipprob: float
    precipcover: float
    preciptype: Optional[List[str]] = None  # Marked as Optional
    snow: float
    snowdepth: float
    windgust: float
    windspeed: float
    winddir: float
    pressure: float
    cloudcover: float
    visibility: float
    solarradiation: Optional[float] = None  # Marked as Optional
    solarenergy: Optional[float] = None  # Marked as Optional
    uvindex: Optional[int] = None  # Marked as Optional
    sunrise: str
    sunriseEpoch: int
    sunset: str
    sunsetEpoch: int
    moonphase: float
    conditions: str
    description: str
    icon: str
    stations: List[str]
    source: str
    # If normal conditions are not always provided, you could mark this as Optional as well:
    normal: Optional[Normal] = None
    hours: List[Hour]


class WeatherResponse(BaseModel):
    queryCost: int
    latitude: float
    longitude: float
    resolvedAddress: str
    address: str
    timezone: str
    tzoffset: float
    days: List[Day]
    stations: Dict[str, Station]

    def calc_temp(self):
        max_temp = -float('inf')
        min_temp = float('inf')
        n = len(self.days)
        temp_sum = 0.0
        for x in self.days:
            max_temp = max(max_temp, x.tempmax)
            min_temp = min(min_temp, x.tempmin)
            temp_sum += x.temp
        return min_temp, max_temp, temp_sum/n

