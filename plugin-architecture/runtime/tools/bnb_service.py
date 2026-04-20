from typing import Dict, List, TypedDict
from langchain_community.tools import tool


# ----------------------------------------------------------------------------
# B&B booking tool
# ----------------------------------------------------------------------------
class BnBOffer(TypedDict): #A
    bnb_id: int
    bnb_name: str
    town: str
    available_rooms: int
    price_per_room: float

class BnBBookingService: #B
    @staticmethod
    def get_offers_near_town(town: str, num_rooms: int) \
        -> List[BnBOffer]: #C
        # Mocked REST API response: multiple BnBs per destination
        mock_bnb_offers = [ #D
            # Newquay
            {"bnb_id": 1, "bnb_name": "Seaside BnB", 
            "town": "Newquay", "available_rooms": 3, 
            "price_per_room": 80.0},
            {"bnb_id": 2, "bnb_name": "Surfside Guesthouse", 
            "town": "Newquay", "available_rooms": 2, 
            "price_per_room": 85.0},
            # Falmouth
            {"bnb_id": 3, "bnb_name": "Harbour View BnB", 
            "town": "Falmouth", "available_rooms": 4, 
            "price_per_room": 78.0},
            {"bnb_id": 4, "bnb_name": "Seafarer's Rest", 
            "town": "Falmouth", "available_rooms": 1, 
            "price_per_room": 90.0},
            # St Austell
            {"bnb_id": 5, "bnb_name": "Garden Gate BnB", 
            "town": "St Austell", "available_rooms": 2, "price_per_room": 82.0},
            {"bnb_id": 6, "bnb_name": "Coastal Cottage BnB", 
            "town": "St Austell", "available_rooms": 3, "price_per_room": 88.0},
            # Penzance
            {"bnb_id": 7, "bnb_name": "Penzance Pier BnB", 
            "town": "Penzance", "available_rooms": 2, "price_per_room": 95.0},
            {"bnb_id": 8, "bnb_name": "Cornish Charm BnB", 
            "town": "Penzance", "available_rooms": 3, "price_per_room": 87.0},
            # Camborne
            {"bnb_id": 9, "bnb_name": "Camborne Corner BnB", 
            "town": "Camborne", "available_rooms": 2, "price_per_room": 75.0},
            {"bnb_id": 10, "bnb_name": "Rose Cottage BnB", 
            "town": "Camborne", "available_rooms": 2, "price_per_room": 79.0},
            # Hayle
            {"bnb_id": 11, "bnb_name": "Hayle Haven BnB", 
            "town": "Hayle", "available_rooms": 3, "price_per_room": 83.0},
            {"bnb_id": 12, "bnb_name": "Dune View BnB", 
            "town": "Hayle", "available_rooms": 1, "price_per_room": 81.0},
            # Land's End
            {"bnb_id": 13, "bnb_name": "Land's End Lookout BnB", 
            "town": "Land's End", "available_rooms": 2, "price_per_room": 100.0},
            {"bnb_id": 14, "bnb_name": "Atlantic Edge BnB", 
            "town": "Land's End", "available_rooms": 2, "price_per_room": 105.0},
            # Bude
            {"bnb_id": 15, "bnb_name": "Bude Beach BnB", 
            "town": "Bude", "available_rooms": 2, "price_per_room": 77.0},
            {"bnb_id": 16, "bnb_name": "Cliffside BnB", 
            "town": "Bude", "available_rooms": 3, "price_per_room": 80.0},
            # Padstow
            {"bnb_id": 17, "bnb_name": "Padstow Harbour BnB", 
            "town": "Padstow", "available_rooms": 2, "price_per_room": 92.0},
            {"bnb_id": 18, "bnb_name": "Fisherman's Rest BnB", 
            "town": "Padstow", "available_rooms": 2, "price_per_room": 89.0},
            # St Ives
            {"bnb_id": 19, "bnb_name": "St Ives Bay BnB", "town": "St Ives", "available_rooms": 3, "price_per_room": 97.0},
            {"bnb_id": 20, "bnb_name": "Artists' Retreat BnB", "town": "St Ives", "available_rooms": 2, "price_per_room": 102.0},
            # Looe
            {"bnb_id": 21, "bnb_name": "Looe Riverside BnB", "town": "Looe", "available_rooms": 2, "price_per_room": 84.0},
            {"bnb_id": 22, "bnb_name": "Harbour Lights BnB", "town": "Looe", "available_rooms": 2, "price_per_room": 86.0},
            # Polperro
            {"bnb_id": 23, "bnb_name": "Polperro Cove BnB", "town": "Polperro", "available_rooms": 2, "price_per_room": 91.0},
            {"bnb_id": 24, "bnb_name": "Smuggler's Rest BnB", "town": "Polperro", "available_rooms": 2, "price_per_room": 93.0},
            # Mevagissey
            {"bnb_id": 25, "bnb_name": "Mevagissey Harbour BnB", "town": "Mevagissey", "available_rooms": 2, "price_per_room": 90.0},
            {"bnb_id": 26, "bnb_name": "Seafarer's BnB", "town": "Mevagissey", "available_rooms": 2, "price_per_room": 88.0},
            # Port Isaac
            {"bnb_id": 27, "bnb_name": "Port Isaac View BnB", 
            "town": "Port Isaac", "available_rooms": 2, 
            "price_per_room": 99.0},
            {"bnb_id": 28, "bnb_name": "Fisherman's Cottage BnB", 
            "town": "Port Isaac", "available_rooms": 2, 
            "price_per_room": 101.0},
            # Fowey
            {"bnb_id": 29, "bnb_name": "Fowey Quay BnB", 
            "town": "Fowey", "available_rooms": 2, 
            "price_per_room": 94.0},
            {"bnb_id": 30, "bnb_name": "Riverside Rest BnB", 
            "town": "Fowey", "available_rooms": 2, 
            "price_per_room": 96.0},
        ]
        offers = [offer for offer in 
            mock_bnb_offers 
            if offer["town"].lower() == town.lower() 
               and offer["available_rooms"] >= num_rooms]
        return offers


@tool(description="""Chck BnB rom availability and price for a destination in Cornwall.""")
def check_bnb_availability(destination: str, num_rooms: int )-> List[Dict]:
    offers = BnBBookingService.get_offers_near_town(destination, num_rooms)
    if not offers:
        return [{"error": f"No available BnB's found in {destination} for {num_rooms} rooms."}]
    return offers


