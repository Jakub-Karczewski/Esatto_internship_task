import os
from urllib import parse
from typing import Optional, List

import requests
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from pydantic import ConfigDict, BaseModel, Field, EmailStr
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated
from bson import ObjectId
from motor import motor_asyncio
from datetime import datetime
from pymongo import ReturnDocument
from fastapi.responses import JSONResponse
from requests_models import Station, Hour, Normal, WeatherResponse, Day

app = FastAPI()
client = motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
PyObjectId = Annotated[str, BeforeValidator(str)]
db = client.weather
entity_collection = db.get_collection("weather_entities")


class EntityModel(BaseModel):

    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    start_date: datetime = Field(...)
    end_date: datetime = Field(...)
    name: str = Field(...)
    temp_min: float = Field(...)
    temp_max: float = Field(...)
    temp_avg: float = Field(...)
    country_name: str = Field(...)
    town_name: str = Field(...)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Krakow",
                "start_date": datetime(2014, 9, 24, 7, 51, 4),
                "end_date": datetime(2014, 9, 24, 8, 51, 4),
                "temp_min": 30.1,
                "temp_max": 38.2,
                "temp_avg": 35.0,
                "country_name": "Poland",
                "town_name": "Bielsko-Biala"
            }
        },
    )


def get_error(code):
    if 400 <= code < 500:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content="Nie znaleziono")
    elif 500 <= code < 600:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content="Serwis niedostepny")
    else:
        return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content="Niezaimplementowane")


class UpdateEntityModel(BaseModel):

    start_date: datetime = Field(...)
    end_date: datetime = Field(...)
    temp_min: float = Field(...)
    temp_max: float = Field(...)
    temp_avg: float = Field(...)
    country_name: str = Field(...)
    town_name: str = Field(...)
    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={ObjectId: str})


def get_weather_response(place: str, start_date: str, end_date: str):
    my_key1 = "FGVEUJUHFZGCML5PZENXNCEUD"

    addr1 = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{place}{start_date}/{end_date}?unitGroup=metric&key={my_key1}&contentType=json"
    response_weather = requests.get(addr1)
    return response_weather


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r") as f:
        return "\n".join(f.readlines())


@app.post("/entities/", response_description="Add new entity", response_model=EntityModel,
          status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_entity(entity: EntityModel = Body(...)):
    start_date = entity.start_date.isoformat()
    end_date = entity.end_date.isoformat()
    town_full = parse.quote(entity.town_name, safe='') + ", " + parse.quote(entity.country_name, safe='')

    response_weather = get_weather_response(town_full, start_date, end_date)
    code = response_weather.status_code
    print(code)
    if code != 200:
        return get_error(code)

    weather = WeatherResponse.parse_obj(response_weather.json())

    t_min, t_max, t_avg = weather.calc_temp()
    entity.temp_avg, entity.temp_min, entity.temp_max = t_avg, t_min, t_max


    new_entity = await entity_collection.insert_one(entity.model_dump(by_alias=True, exclude={"id"}))
    created_entity = await entity_collection.find_one({"_id": new_entity.inserted_id})
    return created_entity


@app.get("/entities/{ID}", response_description="Get a single entity",
         response_model=EntityModel, response_model_by_alias=False)
async def show_entity(ID: str):

    if (entity := await entity_collection.find_one({"name": ID})) is not None:
        return entity
    raise HTTPException(status_code=404, detail=f"Entity of name: {ID} not found")


@app.put("/entities/{ID}", response_description="Update an entity",
         response_model=EntityModel, response_model_by_alias=False)
async def update_entity(ID: str, entity: UpdateEntityModel = Body(...)):

    entity = {k: v for k, v in entity.model_dump(by_alias=True).items() if v is not None}

    if len(entity) >= 1:
        update_result = await entity_collection.find_one_and_update({"name": ID}, {"$set": entity},
                                                                    return_document=ReturnDocument.AFTER)
        if update_result is not None:
            return update_result
        else:
            raise HTTPException(status_code=404, detail=f"Entity {ID} not found")

    if (existing_entity := await entity_collection.find_one({"name": ID})) is not None:
        return existing_entity

    raise HTTPException(status_code=404, detail=f"Entity {ID} not found")


@app.delete("/entities/{ID}", response_description="Delete an entity")
async def delete_entity(ID: str):

    delete_result = await entity_collection.delete_one({"name": ID})

    if delete_result.deleted_count >= 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Entity {ID} not found")


@app.get("/all_entities/{skip}/{limit}/{sort_by}/{order}", response_description="List all entities")
async def list_items(skip: int = 0, limit: int = 10, sort_by: str = "name", order: int = 1):
    cursor = entity_collection.find({}, {"_id": 0}).sort(sort_by, order).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"elements": [item for item in items]}

