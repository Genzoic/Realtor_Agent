import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from dotenv import load_dotenv
from sheet import *
import sqlite3 
from Mail import *  # Add this import
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
import time
from streamlit.components.v1 import declare_component

import googlemaps


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

def init_db():
    conn = sqlite3.connect('Details.db')  # Connect to SQLite database
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Client_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            preferred_cities TEXT,  -- Store as a comma-separated string
            num_rooms INTEGER,
            num_garages INTEGER,
            basement_needed BOOLEAN,
            num_kids_under_10 INTEGER,
            num_kids_under_18 INTEGER,
            type_of_home_preferred TEXT,
            race TEXT,
            maximum_budget REAL,
            first_email TEXT,
            first_email_date DATE,
            first_email_time TIME,
            follow_up_email TEXT,
            follow_up_email_date DATE,
            follow_up_email_time TIME,
            second_follow_up_email TEXT,
            second_follow_up_email_date DATE,
            second_follow_up_email_time TIME
            
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Property_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            num_rooms INTEGER,
            num_garages INTEGER,
            basement BOOLEAN,  
            type_of_home TEXT ,
            address TEXT NOT NULL,
            cost REAL,
            latitude REAL,
            longitude REAL
        )
    ''')
    conn.commit()
    conn.close()

# Call the function to initialize the database
init_db()

conn = sqlite3.connect('Details.db')
cursor = conn.cursor()

class Email(BaseModel):
    subject: str = Field(description="subject of email")
    body: str = Field(description="body of email")

parser = JsonOutputParser(pydantic_object=Email)

places_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert real estate analyst specializing in location-based recommendations. Your task is to analyze client demographics 
            and suggest specifically relevant places near a property that would be compelling selling points.

            IMPORTANT INSTRUCTIONS:
            1. Generate EXACTLY 3-5 places that would be valuable within a 5-mile radius of the property
            2. ONLY use place types that exist as standard Google Maps business categories
            3. Each suggestion MUST be directly tied to the client's specific details provided
            4. DO NOT suggest generic places without clear relevance to client demographics
            5. DO NOT include explanations or commentary
            6. DO NOT hallucinate or make assumptions beyond provided data

            Consider these MANDATORY factors for place selection:
            - City context: Ensure suggestions make sense for the given city
            - Children's ages: Match to appropriate educational/recreational facilities
            - Cultural background: Include culturally relevant establishments
            - Budget level: Align with client's economic status
            - Family size: Account for household composition

            Example valid place types:
            - park
            - restaurant
            - school
            - shopping_mall
            - gym
            - place_of_worship
            - library
            
    
            OUTPUT FORMAT:
            Return ONLY a comma-separated list of 3-5 place types and optional keywords in the format "type:keyword".
            Example: "restaurant:indian, park, school:elementary"
            
            DO NOT INCLUDE: explanations, descriptions, or any text beyond the comma-separated list."""
        ),
        ("human", """Client Details:
        City: {city}
        Number of kids under 10: {num_kids_under_10}
        Number of kids under 18: {num_kids_under_18} 
        Race: {race}
        Budget: {budget}
        Type of home: {home_type}""")
    ])

chain_places = places_prompt | llm


# Define prompt for generating personalized real estate pitch email
real_estate_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a highly skilled real estate agent. Your task is to craft a personalized email to pitch a property to a potential client. 
        You will be provided with the client's details and a list of nearby places that would be of interest to the client. 
        Your goal is to create a compelling and persuasive email that highlights the property's features and the benefits of the nearby places, 
        making the client eager to make a deal.
        Use only those nearby places that firstly seems relevant to their type as defined in the nearby places json.

        IMPORTANT INSTRUCTIONS:
        1. Use the client's details to tailor the email specifically to their needs and preferences.
        2. Highlight the property's key features and how they align with the client's requirements.
        3. Emphasize the nearby places and explain why they would be valuable to the client.
        4. Maintain a professional and persuasive tone throughout the email.
        5. Ensure the email is concise, clear, and free of any hallucinations or assumptions beyond the provided data.

        OUTPUT FORMAT:
        Provide a single email message that includes an introductory greeting, a personalized pitch, and a courteous closing statement.
        The email should be in JSON format with keys 'subject' and 'body'.
        """
    ),
    ("human", """Client Details:
    Name: {name}
    Email: {email}
    Preferred Cities: {preferred_cities}
    Number of Rooms: {num_rooms}
    Number of Garages: {num_garages}
    Basement Needed: {basement_needed}
    Number of Kids Under 10: {num_kids_under_10}
    Number of Kids Under 18: {num_kids_under_18}
    Type of Home Preferred: {type_of_home_preferred}
    Race: {race}
    Maximum Budget: {maximum_budget}

    Property Details:
    City: {property_city}
    Number of Rooms: {property_num_rooms}
    Number of Garages: {property_num_garages}
    Basement: {property_basement}
    Type of Home: {property_type_of_home}
    Address: {property_address}
    Cost: {property_cost}

    Nearby Places:
    {nearby_places}
     
     Email Sender Name: {sender_name}
    """)
])

chain_real_estate = real_estate_prompt | llm |parser

# Define prompt for generating personalized follow-up real estate email
follow_up_real_estate_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a highly skilled real estate agent crafting a follow-up email. Your task is to create a personalized follow-up email 
        that builds upon previous communications while highlighting new or emphasized property features and nearby amenities.

        IMPORTANT INSTRUCTIONS:
        1. Reference previous communications naturally but don't repeat the same points
        2. Introduce new angles or benefits not previously emphasized
        3. Show awareness of the client's specific needs and preferences
        4. Maintain professional persistence without being pushy
        5. Include a clear call to action
        6. Focus on value propositions most relevant to the client's profile
        7. Make strategic use of nearby amenities information

        Use only verified information provided in the input. Do not make assumptions or include speculative details.

        OUTPUT FORMAT:
        Provide a JSON response with 'subject' and 'body' keys where:
        - subject: A compelling email subject line
        - body: The complete email message including greeting 
        """
    ),
    ("human", """Client Details:
    Name: {name}
    Email: {email}
    Preferred Cities: {preferred_cities}
    Number of Rooms: {num_rooms}
    Number of Garages: {num_garages}
    Basement Needed: {basement_needed}
    Number of Kids Under 10: {num_kids_under_10}
    Number of Kids Under 18: {num_kids_under_18}
    Type of Home Preferred: {type_of_home_preferred}
    Race: {race}
    Maximum Budget: {maximum_budget}

    Property Details:
    City: {property_city}
    Number of Rooms: {property_num_rooms}
    Number of Garages: {property_num_garages}
    Basement: {property_basement}
    Type of Home: {property_type_of_home}
    Address: {property_address}
    Cost: {property_cost}

    Nearby Places:
    {nearby_places}

    Previous Communications:
    First Email: {first_email}
    Follow-up Email: {follow_up_email}
     
    Email Sender Name: {sender_name}
    """)
])

chain_follow_up = follow_up_real_estate_prompt | llm | parser



def get_property_coordinates(address):
        """Get latitude and longitude for a property address using Google Maps Geocoding API"""
        try:
            # Initialize the geocoding client
            gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
            
            # Geocode the address
            result = gmaps.geocode(address)
            
            if result:
                location = result[0]['geometry']['location']
                return location['lat'], location['lng']
            else:
                return None
                
        except Exception as e:
            print(f"Error geocoding address: {e}")
            return None


def find_nearby_places(client_id, property_id):
        # Get client details
        cursor.execute('''
            SELECT cd.num_kids_under_10, cd.num_kids_under_18, cd.race, cd.maximum_budget, pd.city, pd.type_of_home
            FROM Client_details cd
            JOIN Property_details pd ON pd.id = ?
            WHERE cd.id = ?
        ''', (property_id, client_id))
        result = cursor.fetchone()
        
        if not result:
            return []
            
        # Get places recommendation from LLM
        response = chain_places.invoke({
            "city": result[4],
            "num_kids_under_10": result[0],
            "num_kids_under_18": result[1],
            "race": result[2],
            "budget": result[3],
            "home_type": result[5]
        })
        
        return [place.strip() for place in response.content.split(",")]
    


def get_property_location(property_id):
        """Get the coordinates for a property from the database"""
        cursor.execute('SELECT address FROM Property_details WHERE id = ?', (property_id,))
        result = cursor.fetchone()
        
        if result:
            address = result[0]
            return get_property_coordinates(address)
        return None
    

def find_places_near_property(property_location, place_types):
        """Find places of specified types near a property location using Google Places API"""
        if not property_location:
            return []

        try:
            # Initialize the Google Maps client
            print(os.getenv('GOOGLE_MAPS_API_KEY'))
            gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
            
            lat, lng = property_location
            print("inside places function :",lat,lng)
            nearby_places = []
            print("inside place function place_types:",place_types)
            for i in range (len(place_types)):
                print("inside for loop")
                print("place type:",place_types[i])
                # Get places for each place type
                result = gmaps.places_nearby(
                    location=(lat, lng),
                    radius=8000,  # 5 miles = ~8000 meters
                    type=place_types[i].split(':')[0].strip()  # Get the place type before the colon
                )

                # Add any found places to the list
                if result.get('results'):
                    for place in result['results'][:3]:  # Limit to top 3 results per type
                       
            # Calculate and add distance for each place
        
                        place_lat = place['geometry']['location']['lat']
                        place_lng = place['geometry']['location']['lng']
                        
                        # Calculate distance using Google Maps Distance Matrix API
                        ''' distance_result = gmaps.distance_matrix(
                            (lat, lng),
                            (place_lat, place_lng),
                            mode="driving",
                            units="imperial"
                        )
                        
                        if distance_result['rows'][0]['elements'][0]['status'] == 'OK':
                            distance = distance_result['rows'][0]['elements'][0]['distance']['text']
                            place['distance'] = distance
                        else:
                            place['distance'] = 'Unknown'''
                        
                        nearby_places.append({
                            'name': place['name'],
                            'type': place_types[i],
                            'address': place.get('vicinity', 'No address available'),
                            'rating': place.get('rating', 'No rating'),
                            #'distance from property': place['distance']
                        })
           

            return nearby_places

        except Exception as e:
            print(f"Error finding nearby places: {e}")
            return []


def find_matches(client_id):
                            print("client_id:", client_id)
                            # Get client details
                            cursor.execute('''
                                        SELECT c.preferred_cities, c.type_of_home_preferred, c.maximum_budget, c.basement_needed ,c.num_rooms,c.num_garages
                                        FROM Client_details c
                                        WHERE c.id = ?
                                    ''', (int(client_id),))
                            client = cursor.fetchone()
                            print()
                            
                            if not client:
                                print("Client not found")
                                return []
                                
                            # Parse preferred cities from comma-separated string
                            preferred_cities = [city.strip() for city in client[0].split(',')]

                            print("preferred cities:", preferred_cities)
                            #print(client[3].upper())
                            
                            # Get matching properties
                            matches = []
                            query = '''
            SELECT * FROM Property_details 
            WHERE city IN ({})
              AND type_of_home = ?
              AND cost <= ?
              AND basement = ?
              AND num_rooms >= ?
              AND num_garages >= ?
            Order by cost ASC
        '''.format(','.join(['?'] * len(preferred_cities)))
        
                            # Prepare parameters
                            params = tuple(preferred_cities) + (
                                client[1],  # type_of_home
                                float(client[2]),  # maximum_budget
                                client[3],  # basement
                                int(client[4]),  # num_rooms
                                int(client[5])   # num_garages
                            )
                            
                            # Debug print
                            print(f"Executing query: {query}")
                            print(f"Parameters: {params}")
                            try:
                                cursor.execute(query, params)
                                matching_properties = cursor.fetchall()
                                print(f"Found {len(matching_properties)} matching properties")
                                return matching_properties
                                
                            except sqlite3.Error as e:
                                print(f"Database error: {e}")
                                return []
                                
                        
sender_details = {"sender_name": "Shrey", "sender_email": "shreyas.joshi@genzoic.com"}
# Function to initialize the SQLite database and create the table




# ... existing code ...
load_dotenv()
st.set_page_config(layout="wide")

st.markdown("""
    <style>
    div[data-testid="stToolbar"] {
        z-index: 999;
    }
    div[data-testid="stDecoration"] {
        height: 0rem;
    }
    div[data-testid="stToolbar"] button {
        position: fixed;
        top: 0.5rem;
        right: 3rem;
        z-index: 1000;
        border: none;
        background-color: transparent;
        color: inherit;
        padding: 0;
        width: 2rem;
        height: 2rem;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    .stButton > button {
        padding: 0.5rem 1rem;
        font-size: 16px;
        line-height: 1.5;
    }
    </style>
""", unsafe_allow_html=True)


def switch_theme():
    current_theme = st.session_state["themes"]["current_theme"]
    new_theme = "dark" if current_theme == "light" else "light"
    st.session_state["themes"]["current_theme"] = new_theme
    
    theme_options = st.session_state["themes"][new_theme]
    for key, value in theme_options.items():
        if key.startswith("theme"):
            st._config.set_option(key, value)
    
    st.session_state["themes"]["refreshed"] = False
    st.rerun()

if "themes" not in st.session_state:
    st.session_state.themes = {
        "current_theme": "light",
        "refreshed": True,
        "light": {
            "theme.base": "light",
            "theme.primaryColor": "#5591f5",  # Light blue for light theme
            "theme.backgroundColor": "white",
            "theme.secondaryBackgroundColor": "#f0f2f6",
            "theme.textColor": "#31333F",
            "button_face": "🌞"
        },
        "dark": {
            "theme.base": "dark",
            "theme.primaryColor": "#c98bdb",  # Light purple for dark theme
            "theme.backgroundColor": "#0E1117",
            "theme.secondaryBackgroundColor": "#262730",
            "theme.textColor": "#FAFAFA",
            "button_face": "🌜"
        }
    }
with st.sidebar:
    btn_face = st.session_state.themes[st.session_state.themes["current_theme"]]["button_face"]
    st.button(btn_face, on_click=switch_theme, key="theme-switch")


if not st.session_state.themes["refreshed"]:
    st.session_state.themes["refreshed"] = True
    st.rerun()


# Create pages
page = st.sidebar.selectbox("Choose a page", ["Configurations", "Customizations"])
# Set up session state to store data between interactions





if page == "Configurations":
    # Input for URLs
    col1, col2 = st.columns([0.8, 0.2])
    
    # Initialize state for confirmation
    if 'show_confirm' not in st.session_state:
        st.session_state.show_confirm = False
    
    with col2:
        if st.button("Clear Configurations", key="clear_config"):
            st.session_state.show_confirm = True
    
    # Show confirmation dialog
    if st.session_state.show_confirm:
        st.error("Do you confirm to clear the configurations?")
        col1, col2 = st.columns([0.5, 0.5])
        
        with col1:
            if st.button("Confirm", key="confirm_clear"):
                try:
                    # Clear client URL file
                    if os.path.exists("client_url.txt"):
                        with open("client_url.txt", 'w') as f:
                            f.write('')
                    
                    # Clear property URL file
                    if os.path.exists("property_url.txt"):
                        with open("property_url.txt", 'w') as k:
                            k.write('')
                    
                    # Remove database file
                    if os.path.exists("Details.db"):
                        cursor.execute("Delete from Client_details")
                        cursor.execute("Delete from Property_details")
                        conn.commit()
                    
                    st.session_state.show_confirm = False
                    st.success("Configurations cleared successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing configurations: {str(e)}")
        
        with col2:
            if st.button("Cancel", key="cancel_clear"):
                st.session_state.show_confirm = False
                st.rerun()

    st.title("Configurations")


    
    if "property_url" not in st.session_state:
        st.session_state["property_url"]=""
    
    if "client_url" not in st.session_state:
        st.session_state["client_url"]=""

    if 'spreadsheet_id' not in st.session_state:
        st.session_state.spreadsheet_id = ''
    if 'creds' not in st.session_state:
        st.session_state.creds = None
    if 'service' not in st.session_state:
        st.session_state.service = None
    if 'preview' not in st.session_state:
        st.session_state.preview = False
    if 'records' not in st.session_state:
        st.session_state.records = []
    if 'num_records' not in st.session_state:
        st.session_state.num_records = 5
    if 'follow_up' not in st.session_state:
        st.session_state.follow_up = False
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'header' not in st.session_state:
        st.session_state.header = None
    


    present_property_url=""
    if os.path.exists("property_url.txt"):
        f=open("property_url.txt","r")
        present_property_url=f.read()
        f.close()
        #print("present_urls",present_urls)
    
    present_client_url=""
    if os.path.exists("client_url.txt"):
        f=open("client_url.txt","r")
        present_client_url=f.read()
        f.close()
        #print("present_urls",present_urls)
    

    
    property_url = st.text_input("Enter google sheet url for property details", key="property_text_box",value=present_property_url)
    st.session_state.property_url=property_url
    

    if st.button("Submit Property Sheet URL",key="property_url_button"):
        #st.write("Submit button pressed.")  # Debugging statement
        #if st.session_state[url_key]:
            #st.write("Google Sheet URL provided.")  # Debugging statement
            try:
                if 'property_url' in st.session_state:
                    print("property_url found in session state:", st.session_state.property_url)
                else:
                    print("property_url not found in session state")

                # Attempt to write the property_url to a file
                with open("property_url.txt", "w") as f:
                    f.write(st.session_state['property_url'])
                    print("property_url written to file successfully")
                st.session_state.spreadsheet_id = get_spreadsheet_id(st.session_state['property_url'])
                st.session_state.creds = authenticate()
                st.session_state.service = build('sheets', 'v4', credentials=st.session_state.creds)
                st.session_state.df = display_sheet_records(st.session_state.service, st.session_state.spreadsheet_id)
                st.session_state.preview = True
                st.session_state.follow_up = True
                st.write(" Property details loaded successfully.")
                #st.write(st.session_state.df)  # Debugging statement
                
                # Add details to the company database
                for index, row in st.session_state.df.iterrows():
                    
                    city = row['City']
                    num_rooms = row['Num_rooms']
                    num_garages = row['Num_garages']
                    basement = row['Basement']
                    type_of_home = row['Type_of_home']
                    address = row['Address']
                    cost = row['Cost'] 
                    coordinates = get_property_coordinates(address)
                    if coordinates:
                        latitude, longitude = coordinates
                    else:
                        latitude, longitude = None, None

                    
                    cursor.execute('''INSERT INTO Property_details (city, num_rooms, num_garages, basement, type_of_home, address, cost,latitude,longitude) VALUES (?, ?, ?, ?, ?, ?, ?,?,?)''', (city, num_rooms, num_garages, basement, type_of_home, address, cost,latitude,longitude))
                    conn.commit()
                    
                   
            except Exception as e:
                st.error(f"An error occurred: {e}")  # Error handling
    
        
    

      
    client_url = st.text_input("Enter google sheet url for client details",key="client_text_box", value=present_client_url)
    st.session_state.client_url=client_url

    if st.button("Submit Client Sheet URL",key="client_url_button") :
        #st.write("Submit button pressed.")  # Debugging statement
        #if st.session_state[url_key]:
            #st.write("Google Sheet URL provided.")  # Debugging statement
            try:
                g=open("client_url.txt","w")
                g.write(st.session_state['client_url'])
                st.session_state.spreadsheet_id = get_spreadsheet_id(st.session_state['client_url'])
                st.session_state.creds = authenticate()
                st.session_state.service = build('sheets', 'v4', credentials=st.session_state.creds)
                st.session_state.df = display_sheet_records(st.session_state.service, st.session_state.spreadsheet_id)
                st.session_state.preview = True
                st.session_state.follow_up = True
                st.write("Client details loaded successfully.")
                #st.write(st.session_state.df)  # Debugging statement
                
                # Add details to the company database
                for index, row in st.session_state.df.iterrows():
                    name = row['Name']
                    email = row['Email']
                    preferred_cities = row['Preferred_cities']
                    num_rooms = row['Num_rooms']
                    num_garages = row['Num_garages']
                    basement_needed = row['Basement_needed']
                    num_kids_under_10 = row['Num_kids_under_10']
                    num_kids_under_18 = row['Num_kids_under_18']
                    type_of_home_preferred = row['Type_of_home_preferred']
                    race = row['Race']
                    maximum_budget = row['Maximum_budget']
                    
                    cursor.execute('''INSERT INTO Client_details (name, email, preferred_cities, num_rooms, num_garages, basement_needed, num_kids_under_10, num_kids_under_18, type_of_home_preferred, race, maximum_budget,first_email,first_email_date,first_email_time,follow_up_email,follow_up_email_date,follow_up_email_time,second_follow_up_email,second_follow_up_email_date,second_follow_up_email_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?)''', (name, email, preferred_cities, num_rooms, num_garages, basement_needed, num_kids_under_10, num_kids_under_18, type_of_home_preferred, race, maximum_budget,None,None,None,None,None,None,None,None,None))
                    conn.commit()
                    
                   
            except Exception as e:
                st.error(f"An error occurred: {e}")  # Error handling
    
    elif (st.session_state.client_url!=''):
         st.session_state.preview = True
         st.session_state.follow_up = True
        
    

elif page == "Customizations":

    st.title("Customizations")
    if 'selected_row' not in st.session_state:
            st.session_state.selected_row = None
    if st.session_state.preview:
        print("preview")
        cursor.execute("SELECT * FROM Client_details")
        rows = cursor.fetchall()
        
        # Create a DataFrame with all columns from the database
        df_all_columns = pd.DataFrame(rows)
        
        # Define the columns you want to use
        columns = ['id', 'Name', 'Email', 'Preferred Cities', 'Num Rooms', 'Num Garages', 'Basement Needed', 'Num Kids Under 10', 'Num Kids Under 18', 'Type of Home Preferred', 'Race', 'Maximum Budget']
        
        # Select only the specified columns
        st.session_state.df = df_all_columns.loc[:, :len(columns)-1]
        st.session_state.df.columns = columns
        
        with st.sidebar:
            st.write("## Client Details")
        
        # Create radio buttons for row selection
            selected_client = st.radio(
                "Select a client",
                options=st.session_state.df['Name'].unique(),
                format_func=lambda x: f"{x} - {st.session_state.df[st.session_state.df['Name'] == x]['Email'].iloc[0]}",
                key="client_selector"
            )
            
        # Update selected_row based on radio button selection
        if selected_client:
            st.session_state.selected_row = st.session_state.df[st.session_state.df['Name'] == selected_client].iloc[0]
        
        # Main area display (right side)
        if st.session_state.selected_row is not None:
                
                cursor.execute('SELECT * FROM Client_details WHERE id = ?', (int(st.session_state.selected_row['id']),))
                fetched_row = cursor.fetchone()
                if fetched_row is None:
                    st.error("No client details found in database")
                   

                st.write(f"Details for {st.session_state.selected_row['Name']}:")
                selected_df = st.session_state.df.loc[st.session_state.df['Name'] == st.session_state.selected_row['Name']]
                
                st.dataframe(selected_df[['Name', 'Email', 'Preferred Cities', 'Num Rooms', 'Num Garages', 'Basement Needed', 'Num Kids Under 10', 'Num Kids Under 18', 'Type of Home Preferred', 'Race', 'Maximum Budget']])
               
                print("\n\n")
                print("fetched row",fetched_row)
                # Display matching properties
                print("selected row",st.session_state.selected_row['id'])
                matching_properties = find_matches(st.session_state.selected_row['id'])

                if matching_properties:
                    st.write("Matching Properties:")
                    matching_df = pd.DataFrame(matching_properties, columns=['ID', 'City', 'Number of Rooms', 'Number of Garages', 'Basement', 'Type of Home', 'Address', 'Cost', 'Latitude', 'Longitude'])
                    st.dataframe(matching_df[['City', 'Number of Rooms', 'Number of Garages', 'Basement', 'Type of Home', 'Address', 'Cost']])
                else:
                    st.write("No matching properties found.")
                
                

                if 'generated_email' not in st.session_state:
                    st.session_state.generated_email = None
                if 'show_send_buttons' not in st.session_state:
                    st.session_state.show_send_buttons = False
                
                #st.session_state.generated_email=''
                #st.session_state.show_send_buttons=False

                # Separate the email gener ation button
                #print("source_data", st.session_state.source_company_data)
                #print(fetched_row[3])
                #if fetched_row[7] is not None :
                    #st.warning(f"No response has been recieved from {fetched_row[1]}")

    
                if fetched_row[12] is None:
                   
                        # Insert code for generating follow up email here
                    if st.button("Generate Personalized Email", key="generate_email"):
                        try:
                            
                            with st.spinner(f"Searching for nearby places for matched properties..."):
                                time.sleep(2)
                                nearby = {}
                                for i in st.session_state.selected_row['Preferred Cities'].split(","):
                                    response = chain_places.invoke({
                                                    "city": i,  # changed from City
                                                    "num_kids_under_10": st.session_state.selected_row['Num Kids Under 10'],  # changed from Number of kids under 10
                                                    "num_kids_under_18": st.session_state.selected_row['Num Kids Under 18'],  # changed from Number of kids under 18
                                                    "race": st.session_state.selected_row['Race'],  # changed from Race
                                                    "budget": st.session_state.selected_row['Maximum Budget'],  # changed from Budget
                                                    "home_type": st.session_state.selected_row['Type of Home Preferred']  # changed from Type of home
                                                })
                                    print(type(response.content),response.content)
                                    type_keyword=response.content.split(',')
                                    

                                    nearby[i] = type_keyword
                                    #nearby[i] = response.content.split(',')
                                
                                places_near_property ={}
                                count=0
                                for j in matching_properties:
                                    if(count==1):
                                        break
                                    #print("Inside loop  ",j[6],get_property_coordinates(j[6]))
                                    cursor.execute("SELECT latitude, longitude  FROM Property_details WHERE address = ?", (j[6],))
                                    coordinates = cursor.fetchone()
                                    print("Inside lopp nearby general places",nearby[j[1]])
                                    response=find_places_near_property(coordinates,nearby[j[1]])
                                    places_near_property[j[6]]=response
                                    count+=1

                                print("\n\n\n")
                                print("print places nearby ",places_near_property)
                                #for i in matching_properties:

                            
                            #print(nearby)
                            #print(st.session_state.target_company_data)
                            #if st.session_state.target_company_data != '':
                                # with st.expander("Target Company Data"):
                                    #   st.text_area("", value=st.session_state.target_company_data, height=300, disabled=True)
                            
                            #with st.spinner(f"Researching {st.session_state.selected_row['Member Name']} in Linkedin..."):
                            # time.sleep(2)
                            
                        # with st.expander("Company Member Details"):
                            # st.text_area("", value=st.session_state.selected_row['Linkedin Profile'], height=300, disabled=True)
                                
                            with st.spinner("Creating personalized email with all the information..."):
                                time.sleep(2)
                                final_response = chain_real_estate.invoke({
                                    "name": st.session_state.selected_row['Name'],
                                    "email": st.session_state.selected_row['Email'],
                                    "preferred_cities": st.session_state.selected_row['Preferred Cities'],
                                    "num_rooms": st.session_state.selected_row['Num Rooms'],
                                    "num_garages": st.session_state.selected_row['Num Garages'],
                                    "basement_needed": st.session_state.selected_row['Basement Needed'],
                                    "num_kids_under_10": st.session_state.selected_row['Num Kids Under 10'],
                                    "num_kids_under_18": st.session_state.selected_row['Num Kids Under 18'],
                                    "type_of_home_preferred": st.session_state.selected_row['Type of Home Preferred'],
                                    "race": st.session_state.selected_row['Race'],
                                    "maximum_budget": st.session_state.selected_row['Maximum Budget'],
                                    "property_city": matching_properties[0][1],
                                    "property_num_rooms": matching_properties[0][2],
                                    "property_num_garages": matching_properties[0][3],
                                    "property_basement": matching_properties[0][4],
                                    "property_type_of_home": matching_properties[0][5],
                                    "property_address": matching_properties[0][6],
                                    "property_cost": matching_properties[0][7],
                                    "nearby_places": places_near_property[matching_properties[0][6]],
                                    "sender_name": "Genzoic",
                                })
                            
                            # Store the generated email in session state
                        
                            st.session_state.generated_email = final_response
                            st.session_state.show_send_buttons = True
                            print("generated personalized email",st.session_state.generated_email)
                            
                        except Exception as e:
                            st.error(f"An error occurred during email generation: {e}")
                            print(f"Error: {e}")
                else:
                  
               
                       
                    
                    if fetched_row[12] is not None:
                        with st.expander(f"First Email Sent on  {fetched_row[13]} at {fetched_row[14]}"):
                           st.text_area("", value=fetched_row[12], height=300, disabled=True)
                        
                    if fetched_row[15] is not None:
                        #print(fetched_row[9])
                        with st.expander(f"Follow up Email Sent on {fetched_row[16]} at {fetched_row[17]}"):
                            st.text_area("", value=fetched_row[15], height=300, disabled=True)
                            
                    if fetched_row[18] is not None:
                       with st.expander(f"Second Follow up Email Sent on {fetched_row[19]} at {fetched_row[20]}"):
                         st.text_area("", value=fetched_row[18], height=300, disabled=True)  
                      # Adjust height as needed
# ... existing code ... # Display the previous email
                    if(fetched_row[18] is None):
                        print("Second folow up email not sent")
                        if st.button("Generate Personalized Follow-Up Email", key="generate_follow_up_email"):
                         try:

                           
                                with st.spinner(f"Searching for nearby places for matched properties..."):
                                    time.sleep(2)
                                    nearby = {}
                                    for i in st.session_state.selected_row['Preferred Cities'].split(","):
                                        response = chain_places.invoke({
                                            "city": i,
                                            "num_kids_under_10": st.session_state.selected_row['Num Kids Under 10'],
                                            "num_kids_under_18": st.session_state.selected_row['Num Kids Under 18'], 
                                            "race": st.session_state.selected_row['Race'],
                                            "budget": st.session_state.selected_row['Maximum Budget'],
                                            "home_type": st.session_state.selected_row['Type of Home Preferred']
                                        })
                                        type_keyword = response.content.split(',')
                                        nearby[i] = type_keyword

                                    places_near_property = {}
                                    count = 0
                                    for j in matching_properties:
                                        if count == 1:
                                            break
                                        cursor.execute("SELECT latitude, longitude FROM Property_details WHERE address = ?", (j[6],))
                                        coordinates = cursor.fetchone()
                                        response = find_places_near_property(coordinates, nearby[j[1]])
                                        places_near_property[j[6]] = response
                                        count += 1

                                with st.spinner("Creating personalized email with all the information..."):
                                    time.sleep(2)
                                    final_response = chain_follow_up.invoke({
                                        "name": st.session_state.selected_row['Name'],
                                        "email": st.session_state.selected_row['Email'], 
                                        "preferred_cities": st.session_state.selected_row['Preferred Cities'],
                                        "num_rooms": st.session_state.selected_row['Num Rooms'],
                                        "num_garages": st.session_state.selected_row['Num Garages'],
                                        "basement_needed": st.session_state.selected_row['Basement Needed'],
                                        "num_kids_under_10": st.session_state.selected_row['Num Kids Under 10'],
                                        "num_kids_under_18": st.session_state.selected_row['Num Kids Under 18'],
                                        "type_of_home_preferred": st.session_state.selected_row['Type of Home Preferred'],
                                        "race": st.session_state.selected_row['Race'],
                                        "maximum_budget": st.session_state.selected_row['Maximum Budget'],
                                        "property_city": matching_properties[0][1],
                                        "property_num_rooms": matching_properties[0][2], 
                                        "property_num_garages": matching_properties[0][3],
                                        "property_basement": matching_properties[0][4],
                                        "property_type_of_home": matching_properties[0][5],
                                        "property_address": matching_properties[0][6],
                                        "property_cost": matching_properties[0][7],
                                        "nearby_places": places_near_property[matching_properties[0][6]],
                                        "first_email": fetched_row[12],
                                        "follow_up_email": fetched_row[15],
                                        "sender_name": "Genzoic"
                                    })
                        
                                    
                                    print(final_response)
                            
                           
                                st.session_state.generated_email = final_response
                                st.session_state.show_send_buttons = True
                           
                            
                         except Exception as e:
                            st.error(f"An error occurred during email generation: {e}")
                            print(f"Error: {e}")
                    
                    else:
                      st.warning(f"No more follow-up emails allowed for {st.session_state.selected_row['Name']}")

                    # Show the generated email if it exists
                    
                if st.session_state.generated_email:
                    st.write("Generated Email:")
                    #st.text_area("Generated Email:",value=f"Subject :{st.session_state.generated_email.get('subject', '')}" + "\n" +f"{st.session_state.generated_email['body']}")
                    #st.write(st.session_state.generated_email['body'])
                    full_email = f"Subject: {st.session_state.generated_email.get('subject', '')}\n\n{st.session_state.generated_email.get('body', '')}"
                    edited_email = st.text_area(
                    "",
                    value=full_email,
                    height=300,
                    key="edit_full_email"
                )
                
                # Split the edited email back into subject and body
                    if edited_email:
                        lines = edited_email.split("\n", 1)  # Split only on the first newline
                        if len(lines) > 1:
                            edited_subject = lines[0].replace("Subject: ", "").strip()  # Remove "Subject: " prefix
                            edited_body = lines[1].strip()
                        else:
                            edited_subject = lines[0].replace("Subject: ", "").strip()
                            edited_body = ""
                        
                        # Store edited version back in session state
                        st.session_state.generated_email = {
                            'subject': edited_subject,
                            'body': edited_body
                        }


                # Show send/cancel buttons if email was generated
                if st.session_state.show_send_buttons:
                    print("buttons present")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Send Email", key="send_email"):
                            print("Send email ")
                            try:
                                current_time = time.localtime()
                                current_date = time.strftime('%Y-%m-%d', current_time)
                                current_time_str = time.strftime('%H:%M:%S', current_time)
                                
                                send_email('smtp.gmail.com', 587, sender_details["sender_email"], os.getenv('password'), 
                                        sender_details["sender_email"], fetched_row[2], 
                                        st.session_state.generated_email["subject"], 
                                        st.session_state.generated_email["body"])
                                
                                if fetched_row[12] is None:
                                    print("First email sent")
                                    cursor.execute('''
                                        UPDATE Client_details 
                                        SET first_email = ?, first_email_date = ?, first_email_time = ?
                                        WHERE id = ?
                                    ''', (
                                        st.session_state.generated_email["subject"] + "\n" + st.session_state.generated_email['body'],
                                        current_date,
                                        current_time_str,
                                        fetched_row[0]
                                    ))
                                elif fetched_row[15] is None:
                                    cursor.execute('''
                                        UPDATE Client_details 
                                        SET follow_up_email = ?, follow_up_email_date = ?, follow_up_email_time = ?
                                         WHERE id=?
                                    ''', (
                                        st.session_state.generated_email["subject"] + "\n" + st.session_state.generated_email['body'],
                                        current_date,
                                        current_time_str,
                                        fetched_row[0]
                                    ))
                                else:
                                    cursor.execute('''
                                        UPDATE Client_details 
                                        SET second_follow_up_email = ?, second_follow_up_email_date = ?, second_follow_up_email_time = ?
                                        WHERE id=?
                                    ''', (
                                        st.session_state.generated_email["subject"] + "\n" + st.session_state.generated_email['body'],
                                        current_date,
                                        current_time_str,
                                        fetched_row[0]
                                    ))
                                conn.commit()
                                st.success("Email sent successfully!")
                                # Reset states after successful send
                                st.session_state.generated_email = None
                                st.session_state.show_send_buttons = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error sending email: {e}")
                    
                    with col2:
                        if st.button("Cancel", key="cancel_email"):
                            st.session_state.generated_email = None
                            st.session_state.show_send_buttons = False
                            st.rerun()
                  
                       

   


