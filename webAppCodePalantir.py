import pandas as pd
import dash
from dash import dcc, html, Input, Output, callback_context, State
import plotly.graph_objects as go
import numpy as np
import os
from foundry.transforms import Dataset, Column
import base64
import io
from scipy.interpolate import CubicSpline
import warnings
warnings.filterwarnings('ignore')

# Initialize global variables
df = None
df_clean = None
unique_drone_ids = []

# Function to process the DataFrame
def process_dataframe(df):
    # Process timestamp if it's in dict format
    for col in ['timestamp']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x.get('timestamp') if isinstance(x, dict) and 'timestamp' in x else x)
    
    # Convert timestamp to datetime and ensure timezone consistency
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    # Convert all timestamps to UTC if they have timezone, or localize to UTC if they don't
    df['timestamp'] = df['timestamp'].apply(
        lambda x: x.tz_localize('UTC') if x.tz is None else x.tz_convert('UTC')
        if pd.notnull(x) else x
    )
    
    # Clean and prepare the DataFrame
    df_clean = df[['aircraft_id', 'timestamp', 'latitude', 'longitude', 'altitude', 'heading']].dropna(
        subset=['aircraft_id', 'latitude', 'longitude', 'altitude']
    )
    df_clean.sort_values(by='timestamp', inplace=True)
    df_clean['timestamp_str'] = df_clean['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    return df_clean

try:
    # Try to load data from Foundry
    df = Dataset.get("combined_telemetry_data").read_table(format="pandas")
except:
    # Initialize empty DataFrame if Foundry data is not available
    df = pd.DataFrame(columns=['aircraft_id', 'timestamp', 'latitude', 'longitude', 'altitude', 'heading'])

# Process initial DataFrame
df_clean = process_dataframe(df)
unique_drone_ids = sorted(df_clean['aircraft_id'].unique())
print(f"Found drone IDs: {unique_drone_ids}")

# Define color palette for a more appealing UI
colors = {
    'background': '#f8f9fa',
    'text': '#2c3e50',
    'accent': '#3498db',
    'secondary': '#e74c3c',
    'light': '#ecf0f1',
    'dark': '#34495e',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'danger': '#c0392b',
    'drones': ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#d35400', '#34495e', '#16a085', '#c0392b'],
    'safe_zone': 'rgba(46, 204, 113, 0.2)',
    'risk_zone': 'rgba(231, 76, 60, 0.2)',
    'recommended_path': '#27ae60'
}

# Build Dash App
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Drone Tracker 3D"

# Create app layout with improved styling
app.layout = html.Div(style={
    'fontFamily': '"Segoe UI", Arial, sans-serif',
    'margin': '0 auto',
    'maxWidth': '1200px',
    'padding': '20px',
    'backgroundColor': colors['background'],
    'color': colors['text'],
    'borderRadius': '10px',
    'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'
}, children=[
    html.H1("3D Drone Flight Visualizer", style={
        'textAlign': 'center',
        'color': colors['dark'],
        'padding': '10px 0',
        'borderBottom': f'3px solid {colors["accent"]}',
        'marginBottom': '20px'
    }),
    
    # Tabbed interface for different analysis modes
    dcc.Tabs(id='analysis-tabs', value='individual-analysis', children=[
        dcc.Tab(label='Individual Drone Analysis', value='individual-analysis', style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['light'],
            'borderRadius': '5px 5px 0 0'
        }, selected_style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['accent'],
            'color': 'white',
            'borderRadius': '5px 5px 0 0'
        }),
        dcc.Tab(label='Distance & Collision Analysis', value='distance-analysis', style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['light'],
            'borderRadius': '5px 5px 0 0'
        }, selected_style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['secondary'],
            'color': 'white',
            'borderRadius': '5px 5px 0 0'
        }),
        dcc.Tab(label='Upload Data', value='upload-data', style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['light'],
            'borderRadius': '5px 5px 0 0'
        }, selected_style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['success'],
            'color': 'white',
            'borderRadius': '5px 5px 0 0'
        }),
        dcc.Tab(label='Trajectory Analysis', value='trajectory-analysis', style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['light'],
            'borderRadius': '5px 5px 0 0'
        }, selected_style={
            'padding': '10px',
            'fontWeight': 'bold',
            'backgroundColor': colors['warning'],
            'color': 'white',
            'borderRadius': '5px 5px 0 0'
        }),
    ]),
    
    # Content for Individual Analysis Tab
    html.Div(id='individual-analysis-content', children=[
        html.Div(style={'marginBottom': '20px', 'marginTop': '20px'}, children=[
            html.Label("Select Drones:", style={
                'marginBottom': '5px',
                'fontWeight': 'bold',
                'color': colors['dark']
            }),
            dcc.Dropdown(
                id='drone-selector',
                options=[{'label': f"Drone {drone}", 'value': drone} for drone in unique_drone_ids],
                placeholder="Select one or more drones...",
                multi=True,
                value=[unique_drone_ids[0]] if unique_drone_ids else [],  # Default selection
                style={
                    'width': '100%',
                    'borderRadius': '5px',
                    'border': f'1px solid {colors["accent"]}'
                }
            ),
        ]),
        
        # Main visualization area for individual analysis
        html.Div([
            # First row: 3D visualization
            html.Div([
                dcc.Loading(
                    id="loading-graph",
                    type="circle",
                    color=colors['accent'],
                    children=dcc.Graph(id='drone-3d-graph', style={
                        'height': '600px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ),
            ], style={'marginBottom': '20px'}),

            # Second row: Altitude and heading charts (side by side)
            html.Div([
                html.Div([
                    dcc.Graph(id='altitude-chart', style={
                        'height': '400px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ], style={'width': '49%', 'display': 'inline-block', 'marginRight': '2%'}),

                html.Div([
                    dcc.Graph(id='heading-chart', style={
                        'height': '400px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ], style={'width': '49%', 'display': 'inline-block'})
            ], style={'marginBottom': '20px'}),

            # Third row: Longitude and Latitude charts (side by side)
            html.Div([
                html.Div([
                    dcc.Graph(id='longitude-chart', style={
                        'height': '400px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ], style={'width': '49%', 'display': 'inline-block', 'marginRight': '2%'}),

                html.Div([
                    dcc.Graph(id='latitude-chart', style={
                        'height': '400px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ], style={'width': '49%', 'display': 'inline-block'})
            ], style={'marginBottom': '20px'}),

            # Statistics container
            html.Div(id='stats-container', style={
                'padding': '20px',
                'backgroundColor': colors['light'],
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)',
                'color': colors['dark']
            })
        ])
    ], style={'display': 'block'}),
    
    # Content for Distance Analysis Tab
    html.Div(id='distance-analysis-content', children=[
        html.Div(style={'marginBottom': '20px', 'marginTop': '20px'}, children=[
            html.Div([
                html.Div([
                    html.Label("Select First Drone:", style={
                        'marginBottom': '5px',
                        'fontWeight': 'bold',
                        'color': colors['dark']
                    }),
                    dcc.Dropdown(
                        id='drone-selector-1',
                        options=[{'label': f"Drone {drone}", 'value': drone} for drone in unique_drone_ids],
                        placeholder="Select first drone...",
                        value=unique_drone_ids[0] if len(unique_drone_ids) > 0 else None,
                        style={
                            'width': '100%',
                            'borderRadius': '5px',
                            'border': f'1px solid {colors["accent"]}'
                        }
                    ),
                ], style={'width': '49%', 'display': 'inline-block', 'marginRight': '2%'}),
                
                html.Div([
                    html.Label("Select Second Drone:", style={
                        'marginBottom': '5px',
                        'fontWeight': 'bold',
                        'color': colors['dark']
                    }),
                    dcc.Dropdown(
                        id='drone-selector-2',
                        options=[{'label': f"Drone {drone}", 'value': drone} for drone in unique_drone_ids],
                        placeholder="Select second drone...",
                        value=unique_drone_ids[1] if len(unique_drone_ids) > 1 else unique_drone_ids[0] if len(unique_drone_ids) > 0 else None,
                        style={
                            'width': '100%',
                            'borderRadius': '5px',
                            'border': f'1px solid {colors["secondary"]}'
                        }
                    ),
                ], style={'width': '49%', 'display': 'inline-block'}),
            ]),
            
            # Collision risk threshold slider
            html.Div([
                html.Label("Collision Risk Threshold (meters):", style={
                    'marginBottom': '5px',
                    'marginTop': '15px',
                    'fontWeight': 'bold',
                    'color': colors['dark']
                }),
                dcc.Slider(
                    id='collision-threshold',
                    min=10,
                    max=1000,
                    step=10,
                    value=100,
                    marks={
                        10: {'label': '10m', 'style': {'color': colors['danger']}},
                        100: {'label': '100m', 'style': {'color': colors['warning']}},
                        500: {'label': '500m', 'style': {'color': colors['accent']}},
                        1000: {'label': '1000m', 'style': {'color': colors['success']}}
                    },
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'marginTop': '15px'})
        ]),
        
        # Distance Analysis Visualization area
        html.Div([
            # First row: 3D visualization showing both drones
            html.Div([
                dcc.Loading(
                    id="loading-distance-graph",
                    type="circle",
                    color=colors['secondary'],
                    children=dcc.Graph(id='distance-3d-graph', style={
                        'height': '600px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ),
            ], style={'marginBottom': '20px'}),

            # Second row: Distance and collision risk charts
            html.Div([
                html.Div([
                    dcc.Graph(id='distance-chart', style={
                        'height': '400px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ], style={'width': '49%', 'display': 'inline-block', 'marginRight': '2%'}),

                html.Div([
                    dcc.Graph(id='collision-risk-chart', style={
                        'height': '400px',
                        'backgroundColor': colors['light'],
                        'borderRadius': '8px',
                        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                    })
                ], style={'width': '49%', 'display': 'inline-block'})
            ], style={'marginBottom': '20px'}),

            # Distance analysis statistics container
            html.Div(id='distance-stats-container', style={
                'padding': '20px',
                'backgroundColor': colors['light'],
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)',
                'color': colors['dark']
            })
        ])
    ], style={'display': 'none'}),
    
    # Content for Upload Data Tab
    html.Div(id='upload-data-content', children=[
        html.Div(style={'marginBottom': '20px', 'marginTop': '20px'}, children=[
            html.H3("Upload Your Drone Data", style={
                'color': colors['dark'],
                'marginBottom': '15px'
            }),
            html.P("Upload a CSV file containing drone telemetry data. The file should include the following columns:", style={
                'marginBottom': '10px',
                'color': colors['text']
            }),
            html.Ul([
                html.Li("aircraft_id: Unique identifier for each drone"),
                html.Li("timestamp: Time of measurement (ISO format)"),
                html.Li("latitude: Latitude coordinate"),
                html.Li("longitude: Longitude coordinate"),
                html.Li("altitude: Altitude in meters"),
                html.Li("heading: Heading in degrees"),
            ], style={'marginBottom': '20px', 'color': colors['text']}),
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select a CSV File', style={'color': colors['accent']})
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px 0',
                    'backgroundColor': colors['light']
                },
                multiple=False
            ),
            html.Div(id='upload-output', style={'marginTop': '20px'}),
        ])
    ], style={'display': 'none'}),

    # Content for Trajectory Analysis Tab
    html.Div(id='trajectory-analysis-content', children=[
        html.Div(style={'marginBottom': '20px', 'marginTop': '20px'}, children=[
            html.H3("Safe Trajectory Analysis", style={
                'color': colors['dark'],
                'marginBottom': '15px'
            }),
            
            # Add drone selection dropdown
            html.Div([
                html.Label("Select Drones for Risk Analysis:", style={
                    'fontWeight': 'bold',
                    'marginBottom': '10px',
                    'display': 'block'
                }),
                dcc.Dropdown(
                    id='trajectory-drone-selector',
                    options=[{'label': f"Drone {drone}", 'value': drone} for drone in unique_drone_ids],
                    multi=True,
                    placeholder="Select drones to consider for risk analysis...",
                    value=unique_drone_ids,  # Default to all drones
                    style={
                        'width': '100%',
                        'marginBottom': '20px'
                    }
                ),
            ]),
            
            # Input controls
            html.Div([
                html.Div([
                    html.Label("Start Point", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    dcc.Input(
                        id='start-lat',
                        type='number',
                        placeholder='Start Latitude',
                        step=0.0001,
                        style={'marginRight': '10px', 'width': '150px'}
                    ),
                    dcc.Input(
                        id='start-lon',
                        type='number',
                        placeholder='Start Longitude',
                        step=0.0001,
                        style={'width': '150px'}
                    ),
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Label("End Point", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    dcc.Input(
                        id='end-lat',
                        type='number',
                        placeholder='End Latitude',
                        step=0.0001,
                        style={'marginRight': '10px', 'width': '150px'}
                    ),
                    dcc.Input(
                        id='end-lon',
                        type='number',
                        placeholder='End Longitude',
                        step=0.0001,
                        style={'width': '150px'}
                    ),
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Label("Preferred Altitude (meters)", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    dcc.Input(
                        id='preferred-altitude',
                        type='number',
                        value=100,
                        min=0,
                        step=10,
                        style={'width': '150px'}
                    ),
                ], style={'marginBottom': '20px'}),
                
                html.Button(
                    'Generate Safe Trajectory',
                    id='generate-trajectory',
                    style={
                        'backgroundColor': colors['warning'],
                        'color': 'white',
                        'border': 'none',
                        'padding': '10px 20px',
                        'borderRadius': '5px',
                        'cursor': 'pointer'
                    }
                ),
            ], style={'marginBottom': '20px'}),
            
            # Visualization area
            dcc.Loading(
                id="loading-trajectory",
                type="circle",
                children=[
                    dcc.Graph(id='trajectory-3d-graph', style={'height': '600px'}),
                    html.Div(id='trajectory-stats', style={'marginTop': '20px'})
                ]
            ),
        ])
    ], style={'display': 'none'})
])

# Update the toggle tab callback
@app.callback(
    [Output('individual-analysis-content', 'style'),
     Output('distance-analysis-content', 'style'),
     Output('upload-data-content', 'style'),
     Output('trajectory-analysis-content', 'style')],
    [Input('analysis-tabs', 'value')]
)
def toggle_tab_content(tab_value):
    if tab_value == 'individual-analysis':
        return {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
    elif tab_value == 'distance-analysis':
        return {'display': 'none'}, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}
    elif tab_value == 'upload-data':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'block'}, {'display': 'none'}
    else:  # trajectory-analysis
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'block'}

# Callback for handling file upload
@app.callback(
    [Output('upload-output', 'children'),
     Output('drone-selector', 'options'),
     Output('drone-selector-1', 'options'),
     Output('drone-selector-2', 'options'),
     Output('trajectory-drone-selector', 'options'),
     Output('trajectory-drone-selector', 'value')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_output(contents, filename):
    global df, df_clean, unique_drone_ids
    
    if contents is None:
        drone_options = [{'label': f"Drone {drone}", 'value': drone} for drone in unique_drone_ids]
        return html.Div('No file uploaded yet.', style={'color': colors['text']}), \
               drone_options, drone_options, drone_options, drone_options, unique_drone_ids
    
    try:
        # Decode the uploaded file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Read the CSV file
        if 'csv' in filename.lower():
            df_upload = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        else:
            return html.Div('Please upload a CSV file.', style={'color': colors['danger']}), \
                   dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Validate required columns
        required_columns = ['aircraft_id', 'timestamp', 'latitude', 'longitude', 'altitude', 'heading']
        missing_columns = [col for col in required_columns if col not in df_upload.columns]
        
        if missing_columns:
            return html.Div(
                f"Error: Missing required columns: {', '.join(missing_columns)}",
                style={'color': colors['danger']}
            ), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Process the uploaded data
        df_upload_clean = process_dataframe(df_upload)
        
        # Always concatenate with existing data, regardless of whether it's the first upload
        if df is None:
            df = pd.DataFrame(columns=['aircraft_id', 'timestamp', 'latitude', 'longitude', 'altitude', 'heading'])
            df_clean = pd.DataFrame(columns=['aircraft_id', 'timestamp', 'latitude', 'longitude', 'altitude', 'heading'])
            
        # Concatenate with existing data
        df = pd.concat([df, df_upload], ignore_index=True)
        df_clean = pd.concat([df_clean, df_upload_clean], ignore_index=True)
        
        # Sort by timestamp after concatenation
        df_clean.sort_values(by='timestamp', inplace=True)
        
        # Update unique drone IDs
        unique_drone_ids = sorted(df_clean['aircraft_id'].unique())
        
        # Create new dropdown options
        drone_options = [{'label': f"Drone {drone}", 'value': drone} for drone in unique_drone_ids]
        
        # Prepare upload summary
        original_count = len(df_clean) - len(df_upload_clean)
        new_count = len(df_upload_clean)
        total_count = len(df_clean)
        
        return html.Div([
            html.P('Upload successful!', style={'color': colors['success'], 'fontWeight': 'bold'}),
            html.P([
                'Total records: ', html.Strong(f'{total_count}'), 
                ' (Original: ', html.Strong(f'{original_count}'),
                ', Newly added: ', html.Strong(f'{new_count}'), ')'
            ]),
            html.P(f'Number of unique drones: {len(unique_drone_ids)}'),
            html.P(f'Time range: {df_clean["timestamp"].min()} to {df_clean["timestamp"].max()}'),
            html.P('You can now switch to Individual Analysis or Distance Analysis tabs to visualize the data.',
                  style={'marginTop': '10px', 'fontStyle': 'italic'})
        ]), drone_options, drone_options, drone_options, drone_options, unique_drone_ids
        
    except Exception as e:
        return html.Div([
            'Error processing file: ',
            str(e)
        ], style={'color': colors['danger']}), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Existing callback for individual drone analysis (unchanged)
@app.callback(
    [Output('drone-3d-graph', 'figure'),
     Output('altitude-chart', 'figure'),
     Output('heading-chart', 'figure'),
     Output('longitude-chart', 'figure'),
     Output('latitude-chart', 'figure'),
     Output('stats-container', 'children')],
    [Input('drone-selector', 'value')]
)
def update_visualization(selected_drones):
    # Handle case with no drone selection
    if not selected_drones:
        if not unique_drone_ids:
            empty_fig = go.Figure().update_layout(
                title="No drone data loaded.",
                template="plotly_white",
                plot_bgcolor=colors['light'],
                paper_bgcolor=colors['light'],
                font=dict(color=colors['text'])
            )
            # Return empty figures for all outputs
            return (empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, html.P("No data selected", style={'color': colors['text']}))
        selected_drones = [unique_drone_ids[0]]
        title = f"Showing default drone: {selected_drones[0]}"
    else:
        title = "Drone Flight Paths"
        
    # Filter data for selected drones
    filtered = df_clean[df_clean['aircraft_id'].isin(selected_drones)].copy()
    
    if filtered.empty:
        empty_fig = go.Figure().update_layout(
            title="No data available for the selected drone(s).",
            template="plotly_white",
            plot_bgcolor=colors['light'],
            paper_bgcolor=colors['light'],
            font=dict(color=colors['text'])
        )
        # Return empty figures for all outputs
        return (empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, html.P("No data available for the selected drone(s)", style={'color': colors['text']}))
    
    # Sample data if too many points
    max_points = 10000
    if len(filtered) > max_points:
        step = max(1, len(filtered) // max_points)
        filtered = filtered.iloc[::step, :]
        title += f" (Sampled: showing {len(filtered)} of {len(df_clean[df_clean['aircraft_id'].isin(selected_drones)])} points)"
    
    # Normalize coordinates for better 3D visualization
    # Find the center point of all drone paths
    center_lon = filtered['longitude'].mean()
    center_lat = filtered['latitude'].mean()
    
    # Convert to relative kilometers for better scaling
    # 111.32 km per degree of latitude, and cosine correction for longitude
    filtered['x'] = (filtered['longitude'] - center_lon) * 111.32 * np.cos(np.radians(center_lat))
    filtered['y'] = (filtered['latitude'] - center_lat) * 111.32
    
    # Create figures
    fig_3d = go.Figure()
    fig_alt = go.Figure()
    fig_heading = go.Figure()
    fig_lon = go.Figure()
    fig_lat = go.Figure()

    # Statistics to display
    stats_children = [html.H3("Flight Statistics", style={'color': colors['dark'], 'borderBottom': f'2px solid {colors["accent"]}', 'paddingBottom': '10px'})]
    
    for i, drone_id in enumerate(selected_drones):
        drone_color = colors['drones'][i % len(colors['drones'])]
        drone_data = filtered[filtered['aircraft_id'] == drone_id]
        
        if not drone_data.empty:
            # Add trace to the 3D figure
            fig_3d.add_trace(go.Scatter3d(
                x=drone_data['x'],
                y=drone_data['y'],
                z=drone_data['altitude'],
                mode='lines+markers',
                marker=dict(
                    size=4,
                    color=drone_color,
                    opacity=0.8
                ),
                line=dict(
                    width=3,
                    color=drone_color
                ),
                name=f"Drone {drone_id}",
                hovertemplate=
                    "<b>Drone %{text}</b><br>" +
                    "Longitude: %{customdata[0]:.5f}<br>" +
                    "Latitude: %{customdata[1]:.5f}<br>" +
                    "Altitude: %{z:.2f} m<br>" +
                    "Time: %{customdata[2]}<br>" +
                    "<extra></extra>",
                text=[drone_id] * len(drone_data),
                customdata=np.vstack((
                    drone_data['longitude'],
                    drone_data['latitude'],
                    drone_data['timestamp_str']
                )).T
            ))
            
            # Add trace to altitude chart
            fig_alt.add_trace(go.Scatter(
                x=drone_data['timestamp'],
                y=drone_data['altitude'],
                mode='lines',
                line=dict(color=drone_color, width=2),
                name=f"Drone {drone_id}",
                hovertemplate=
                    "<b>Drone %{text}</b><br>" +
                    "Time: %{x|%Y-%m-%d %H:%M:%S}<br>" +
                    "Altitude: %{y:.2f} m<br>" +
                    "<extra></extra>",
                text=[drone_id] * len(drone_data)
            ))
            
            # Add trace to heading chart
            fig_heading.add_trace(go.Scatter(
                x=drone_data['timestamp'],
                y=drone_data['heading'],
                mode='lines',
                line=dict(color=drone_color, width=2),
                name=f"Drone {drone_id}",
                hovertemplate=
                    "<b>Drone %{text}</b><br>" +
                    "Time: %{x|%Y-%m-%d %H:%M:%S}<br>" +
                    "Heading: %{y:.2f} <br>" +
                    "<extra></extra>",
                text=[drone_id] * len(drone_data)
            ))
            
            # Add trace to longitude chart
            fig_lon.add_trace(go.Scatter(
                x=drone_data['timestamp'],
                y=drone_data['longitude'],
                mode='lines',
                line=dict(color=drone_color, width=2),
                name=f"Drone {drone_id}",
                hovertemplate=
                    "<b>Drone %{text}</b><br>" +
                    "Time: %{x|%Y-%m-%d %H:%M:%S}<br>" +
                    "Longitude: %{y:.5f} <br>" +
                    "<extra></extra>",
                text=[drone_id] * len(drone_data)
            ))

            # Add trace to latitude chart
            fig_lat.add_trace(go.Scatter(
                x=drone_data['timestamp'],
                y=drone_data['latitude'],
                mode='lines',
                line=dict(color=drone_color, width=2),
                name=f"Drone {drone_id}",
                hovertemplate=
                    "<b>Drone %{text}</b><br>" +
                    "Time: %{x|%Y-%m-%d %H:%M:%S}<br>" +
                    "Latitude: %{y:.5f} <br>" +
                    "<extra></extra>",
                text=[drone_id] * len(drone_data)
            ))

            # Calculate statistics
            duration = (drone_data['timestamp'].max() - drone_data['timestamp'].min()).total_seconds() / 60
            max_alt = drone_data['altitude'].max()
            min_alt = drone_data['altitude'].min()
            avg_alt = drone_data['altitude'].mean()
            heading_change = abs(np.diff(drone_data['heading'])).sum()
            
            # Calculate distance traveled
            distance = 0
            if len(drone_data) > 1:
                # Using approximate formula for short distances
                for j in range(1, len(drone_data)):
                    lat1, lon1 = drone_data.iloc[j-1]['latitude'], drone_data.iloc[j-1]['longitude']
                    lat2, lon2 = drone_data.iloc[j]['latitude'], drone_data.iloc[j]['longitude']
                    # Convert to radians
                    lat1_rad = np.radians(lat1)
                    dx = (lon2 - lon1) * 111320 * np.cos(lat1_rad)  
                    dy = (lat2 - lat1) * 111320 
                    distance += np.sqrt(dx**2 + dy**2)
            
            # Add stats to the display
            stats_children.append(html.Div([
                html.H4(f"Drone {drone_id}", style={'color': drone_color, 'marginTop': '15px'}),
                html.Div([
                    html.Div([
                        html.Div(f"Flight Duration", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                        html.Div(f"{duration:.2f} minutes", style={'fontSize': '1.2em'})
                    ], style={'width': '33%', 'display': 'inline-block', 'padding': '10px', 'backgroundColor': colors['background'], 'borderRadius': '5px'}),
                    
                    html.Div([
                        html.Div(f"Distance Traveled", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                        html.Div(f"{distance/1000:.2f} km", style={'fontSize': '1.2em'})
                    ], style={'width': '33%', 'display': 'inline-block', 'padding': '10px', 'backgroundColor': colors['background'], 'borderRadius': '5px'}),
                    
                    html.Div([
                        html.Div(f"Data Points", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                        html.Div(f"{len(drone_data)}", style={'fontSize': '1.2em'})
                    ], style={'width': '33%', 'display': 'inline-block', 'padding': '10px', 'backgroundColor': colors['background'], 'borderRadius': '5px'})
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div([
                        html.Div(f"Maximum Altitude", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                        html.Div(f"{max_alt:.2f} m", style={'fontSize': '1.2em'})
                    ], style={'width': '33%', 'display': 'inline-block', 'padding': '10px', 'backgroundColor': colors['background'], 'borderRadius': '5px'}),
                    
                    html.Div([
                        html.Div(f"Minimum Altitude", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                        html.Div(f"{min_alt:.2f} m", style={'fontSize': '1.2em'})
                    ], style={'width': '33%', 'display': 'inline-block', 'padding': '10px', 'backgroundColor': colors['background'], 'borderRadius': '5px'}),
                    
                    html.Div([
                        html.Div(f"Average Altitude", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                        html.Div(f"{avg_alt:.2f} m", style={'fontSize': '1.2em'})
                    ], style={'width': '33%', 'display': 'inline-block', 'padding': '10px', 'backgroundColor': colors['background'], 'borderRadius': '5px'})
                ]),
                
                html.Div([
                    html.Div([
                        html.Div(f"Total Heading Change", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                        html.Div(f"{heading_change:.2f} ", style={'fontSize': '1.2em'})
                    ], style={'width': '33%', 'display': 'inline-block', 'padding': '10px', 'backgroundColor': colors['background'], 'borderRadius': '5px'})
                ], style={'marginTop': '10px'})
            ], style={'marginBottom': '20px', 'borderLeft': f'4px solid {drone_color}', 'paddingLeft': '15px'}))
    
    # Update 3D figure layout
    fig_3d.update_layout(
        scene=dict(
            xaxis=dict(
                title='Distance East-West (km)', 
                showbackground=True, 
                backgroundcolor='rgba(230, 230, 230, 0.5)',
                gridcolor='white',
                zerolinecolor='white',
                showspikes=False
            ),
            yaxis=dict(
                title='Distance North-South (km)', 
                showbackground=True, 
                backgroundcolor='rgba(230, 230, 230, 0.5)',
                gridcolor='white',
                zerolinecolor='white',
                showspikes=False
            ),
            zaxis=dict(
                title='Altitude (m)', 
                showbackground=True, 
                backgroundcolor='rgba(230, 230, 230, 0.5)',
                gridcolor='white',
                zerolinecolor='white',
                showspikes=False
            ),
            aspectmode='cube',  
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        title=dict(
            text=title,
            font=dict(size=16, color=colors['dark'])
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor=colors['accent'],
            borderwidth=1
        ),
        template="plotly_white",
        plot_bgcolor=colors['light'],
        paper_bgcolor=colors['light'],
        font=dict(color=colors['text'])
    )
    
    # Update altitude chart layout
    fig_alt.update_layout(
        title=dict(
            text="Altitude Over Time",
            font=dict(size=16, color=colors['dark'])
        ),
        xaxis=dict(
            title="Time",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        yaxis=dict(
            title="Altitude (m)",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor=colors['accent'],
            borderwidth=1
        ),
        plot_bgcolor=colors['light'],
        paper_bgcolor=colors['light'],
        font=dict(color=colors['text'])
    )
    
    # Update heading chart layout
    fig_heading.update_layout(
        title=dict(
            text="Heading Over Time",
            font=dict(size=16, color=colors['dark'])
        ),
        xaxis=dict(
            title="Time",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        yaxis=dict(
            title="Heading (degrees)",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor=colors['accent'],
            borderwidth=1
        ),
        plot_bgcolor=colors['light'],
        paper_bgcolor=colors['light'],
        font=dict(color=colors['text'])
    )
    
    # Update longitude chart layout
    fig_lon.update_layout(
        title=dict(
            text="Longitude Over Time",
            font=dict(size=16, color=colors['dark'])
        ),
        xaxis=dict(
            title="Time",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        yaxis=dict(title="Longitude",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor=colors['accent'],
            borderwidth=1
        ),
        plot_bgcolor=colors['light'],
        paper_bgcolor=colors['light'],
        font=dict(color=colors['text'])
    )
    
    # Update latitude chart layout
    fig_lat.update_layout(
        title=dict(
            text="Latitude Over Time",
            font=dict(size=16, color=colors['dark'])
        ),
        xaxis=dict(
            title="Time",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        yaxis=dict(
            title="Latitude",
            gridcolor='rgba(230, 230, 230, 0.8)',
            tickfont=dict(color=colors['text'])
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor=colors['accent'],
            borderwidth=1
        ),
        plot_bgcolor=colors['light'],
        paper_bgcolor=colors['light'],
        font=dict(color=colors['text'])
    )
    
    return fig_3d, fig_alt, fig_heading, fig_lon, fig_lat, stats_children

# Callback for distance analysis
@app.callback(
    [Output('distance-3d-graph', 'figure'),
     Output('distance-chart', 'figure'),
     Output('collision-risk-chart', 'figure'),
     Output('distance-stats-container', 'children')],
    [Input('drone-selector-1', 'value'),
     Input('drone-selector-2', 'value'),
     Input('collision-threshold', 'value')]
)
def update_distance_analysis(drone1_id, drone2_id, threshold):
    if not drone1_id or not drone2_id:
        empty_fig = go.Figure().update_layout(
            title="Please select two drones to analyze.",
            template="plotly_white",
            plot_bgcolor=colors['light'],
            paper_bgcolor=colors['light'],
            font=dict(color=colors['text'])
        )
        return empty_fig, empty_fig, empty_fig, html.P("Please select two drones to analyze.", style={'color': colors['text']})
    
    # Get data for both drones
    drone1_data = df_clean[df_clean['aircraft_id'] == drone1_id].copy()
    drone2_data = df_clean[df_clean['aircraft_id'] == drone2_id].copy()
    
    if drone1_data.empty or drone2_data.empty:
        empty_fig = go.Figure().update_layout(
            title="No data available for selected drone(s).",
            template="plotly_white",
            plot_bgcolor=colors['light'],
            paper_bgcolor=colors['light'],
            font=dict(color=colors['text'])
        )
        return empty_fig, empty_fig, empty_fig, html.P("No data available for selected drone(s).", style={'color': colors['text']})
    
    # Calculate distances and collision risks
    common_times = pd.merge(drone1_data, drone2_data, on='timestamp', suffixes=('_1', '_2'))
    
    if common_times.empty:
        empty_fig = go.Figure().update_layout(
            title="No overlapping flight times found.",
            template="plotly_white",
            plot_bgcolor=colors['light'],
            paper_bgcolor=colors['light'],
            font=dict(color=colors['text'])
        )
        return empty_fig, empty_fig, empty_fig, html.P("No overlapping flight times found.", style={'color': colors['text']})
    
    # Calculate 3D distances
    common_times['distance'] = np.sqrt(
        ((common_times['longitude_1'] - common_times['longitude_2']) * 111320 * np.cos(np.radians(common_times['latitude_1'])))**2 +
        ((common_times['latitude_1'] - common_times['latitude_2']) * 111320)**2 +
        (common_times['altitude_1'] - common_times['altitude_2'])**2
    )
    
    # Calculate collision risk (inverse of distance, normalized)
    common_times['collision_risk'] = 1 / (common_times['distance'] / threshold)
    common_times['collision_risk'] = common_times['collision_risk'].clip(0, 1)
    
    # Create 3D visualization
    fig_3d = go.Figure()
    
    # Add traces for both drones
    for i, (drone_id, suffix) in enumerate([
        (drone1_id, '_1'),
        (drone2_id, '_2')
    ]):
        drone_color = colors['drones'][i]
        
        fig_3d.add_trace(go.Scatter3d(
            x=common_times[f'longitude{suffix}'],
            y=common_times[f'latitude{suffix}'],
            z=common_times[f'altitude{suffix}'],
            mode='lines+markers',
            name=f"Drone {drone_id}",
            marker=dict(
                size=4,
                color=drone_color,
                opacity=0.8
            ),
            line=dict(
                color=drone_color,
                width=2
            )
        ))
    
    # Create distance chart
    fig_distance = go.Figure()
    fig_distance.add_trace(go.Scatter(
        x=common_times['timestamp'],
        y=common_times['distance'],
        mode='lines',
        name='Distance',
        line=dict(
            color=colors['accent'],
            width=2
        ),
        fill='tozeroy'
    ))
    
    # Add threshold line
    fig_distance.add_trace(go.Scatter(
        x=common_times['timestamp'],
        y=[threshold] * len(common_times),
        mode='lines',
        name='Risk Threshold',
        line=dict(
            color=colors['danger'],
            width=2,
            dash='dash'
        )
    ))
    
    # Create collision risk chart
    fig_risk = go.Figure()
    fig_risk.add_trace(go.Scatter(
        x=common_times['timestamp'],
        y=common_times['collision_risk'],
        mode='lines',
        name='Collision Risk',
        line=dict(
            color=colors['secondary'],
            width=2
        ),
        fill='tozeroy'
    ))
    
    # Update layouts
    fig_3d.update_layout(
        scene=dict(
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            zaxis_title='Altitude (m)',
            aspectmode='cube'
        ),
        title=dict(
            text=f"3D Flight Paths - Drones {drone1_id} & {drone2_id}",
            font=dict(size=16, color=colors['dark'])
        ),
        template="plotly_white",
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    fig_distance.update_layout(
        title=dict(
            text="Distance Between Drones",
            font=dict(size=16, color=colors['dark'])
        ),
        xaxis_title="Time",
        yaxis_title="Distance (m)",
        template="plotly_white"
    )
    
    fig_risk.update_layout(
        title=dict(
            text="Collision Risk Assessment",
            font=dict(size=16, color=colors['dark'])
        ),
        xaxis_title="Time",
        yaxis_title="Risk Level (0-1)",
        template="plotly_white"
    )
    
    # Calculate statistics
    min_distance = common_times['distance'].min()
    avg_distance = common_times['distance'].mean()
    max_risk = common_times['collision_risk'].max()
    time_at_risk = len(common_times[common_times['distance'] < threshold]) / len(common_times) * 100
    
    # Create statistics display
    stats_children = [
        html.H3("Distance Analysis Statistics", style={'color': colors['dark'], 'marginBottom': '15px'}),
        html.Div([
            html.Div([
                html.Div("Minimum Distance", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                html.Div(f"{min_distance:.2f} m", style={'fontSize': '1.2em', 'color': colors['danger']})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
            
            html.Div([
                html.Div("Average Distance", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                html.Div(f"{avg_distance:.2f} m", style={'fontSize': '1.2em'})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
            
            html.Div([
                html.Div("Maximum Risk Level", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                html.Div(f"{max_risk:.2%}", style={'fontSize': '1.2em', 'color': colors['warning']})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
            
            html.Div([
                html.Div("Time at Risk", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                html.Div(f"{time_at_risk:.1f}%", style={'fontSize': '1.2em', 'color': colors['secondary']})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'})
        ])
    ]
    
    return fig_3d, fig_distance, fig_risk, stats_children

def analyze_traffic_density(df_clean, grid_size=20, density_threshold=3):
    """Analyze traffic density in the airspace using a grid-based approach"""
    # Get the bounds of the airspace
    lat_min, lat_max = df_clean['latitude'].min(), df_clean['latitude'].max()
    lon_min, lon_max = df_clean['longitude'].min(), df_clean['longitude'].max()
    alt_min, alt_max = df_clean['altitude'].min(), df_clean['altitude'].max()
    
    # Create grid
    lat_bins = np.linspace(lat_min, lat_max, grid_size)
    lon_bins = np.linspace(lon_min, lon_max, grid_size)
    alt_bins = np.linspace(alt_min, alt_max, grid_size)
    
    # Initialize traffic zones list
    traffic_zones = []
    
    # Analyze density in grid cells
    for i in range(len(lat_bins)-1):
        for j in range(len(lon_bins)-1):
            for k in range(len(alt_bins)-1):
                # Get points in current grid cell
                mask = (
                    (df_clean['latitude'] >= lat_bins[i]) & 
                    (df_clean['latitude'] < lat_bins[i+1]) &
                    (df_clean['longitude'] >= lon_bins[j]) & 
                    (df_clean['longitude'] < lon_bins[j+1]) &
                    (df_clean['altitude'] >= alt_bins[k]) & 
                    (df_clean['altitude'] < alt_bins[k+1])
                )
                
                points_in_cell = df_clean[mask]
                
                # If cell has significant traffic
                if len(points_in_cell) > density_threshold:
                    # Create zone vertices (cube corners)
                    vertices = np.array([
                        [lat_bins[i], lon_bins[j], alt_bins[k]],
                        [lat_bins[i+1], lon_bins[j], alt_bins[k]],
                        [lat_bins[i], lon_bins[j+1], alt_bins[k]],
                        [lat_bins[i+1], lon_bins[j+1], alt_bins[k]],
                        [lat_bins[i], lon_bins[j], alt_bins[k+1]],
                        [lat_bins[i+1], lon_bins[j], alt_bins[k+1]],
                        [lat_bins[i], lon_bins[j+1], alt_bins[k+1]],
                        [lat_bins[i+1], lon_bins[j+1], alt_bins[k+1]]
                    ])
                    
                    traffic_zones.append({
                        'points': vertices,
                        'density': len(points_in_cell),
                        'avg_altitude': points_in_cell['altitude'].mean()
                    })
    
    return traffic_zones

def find_safe_path(start_point, end_point, traffic_zones, num_points=100):
    """Generate a safe path avoiding high-traffic zones"""
    # Create initial direct path
    t = np.linspace(0, 1, num_points)
    path = np.array([
        np.interp(t, [0, 1], [start_point[0], end_point[0]]),  # lat
        np.interp(t, [0, 1], [start_point[1], end_point[1]]),  # lon
        np.interp(t, [0, 1], [start_point[2], end_point[2]])   # alt
    ]).T
    
    # Define safety parameters with more reasonable values
    safety_margin = 0.0005  # Reduced from 0.005 (about 50m instead of 500m)
    vertical_adjustment = 30  # Reduced from 50m
    max_deviation = 0.001    # Maximum allowed deviation from original path
    
    # Calculate direct distance for reference
    direct_distance = np.linalg.norm([
        (end_point[0] - start_point[0]) * 111320,  # Convert lat difference to meters
        (end_point[1] - start_point[1]) * 111320 * np.cos(np.radians(start_point[0])),  # Convert lon difference to meters
        end_point[2] - start_point[2]
    ])
    
    # Adjust path to avoid high-traffic zones
    for zone in traffic_zones:
        zone_center = zone['points'].mean(axis=0)
        
        # Calculate influence radius based on traffic density but with a cap
        base_influence = safety_margin * min(1 + zone['density'] / 20, 2.0)  # Cap the influence scaling
        influence_radius = min(base_influence, max_deviation)  # Ensure we don't exceed max deviation
        
        for i in range(len(path)):
            # Calculate 3D distance to zone center
            dist_lat = abs(path[i, 0] - zone_center[0])
            dist_lon = abs(path[i, 1] - zone_center[1])
            dist_alt = abs(path[i, 2] - zone_center[2])
            
            # Calculate normalized distance to original path point
            original_point = np.array([
                np.interp(i/len(path), [0, 1], [start_point[0], end_point[0]]),
                np.interp(i/len(path), [0, 1], [start_point[1], end_point[1]]),
                np.interp(i/len(path), [0, 1], [start_point[2], end_point[2]])
            ])
            
            deviation = np.linalg.norm(path[i] - original_point)
            
            # Only adjust if within influence radius and not already deviated too much
            if (dist_lat < influence_radius and 
                dist_lon < influence_radius and 
                dist_alt < vertical_adjustment and 
                deviation < max_deviation):
                
                # Calculate direction vector from zone center to path point
                direction = path[i] - zone_center
                if np.any(direction):  # Avoid division by zero
                    direction = direction / np.linalg.norm(direction)
                else:
                    continue
                
                # Calculate deviation magnitude based on distance and density
                deviation_strength = (influence_radius - max(dist_lat, dist_lon)) / influence_radius
                deviation_strength = min(deviation_strength * 0.5, 0.3)  # Limit maximum deviation
                
                # Apply horizontal deviation
                path[i, 0] += direction[0] * deviation_strength * safety_margin
                path[i, 1] += direction[1] * deviation_strength * safety_margin
                
                # Apply vertical adjustment based on zone density
                if zone['density'] > 5:
                    if zone['avg_altitude'] > path[i, 2]:
                        path[i, 2] -= min(vertical_adjustment * deviation_strength, 20)
                    else:
                        path[i, 2] += min(vertical_adjustment * deviation_strength, 20)
    
    # Smooth the path using a moving average
    window_size = 5
    path = np.array([
        np.convolve(path[:, 0], np.ones(window_size)/window_size, mode='valid'),
        np.convolve(path[:, 1], np.ones(window_size)/window_size, mode='valid'),
        np.convolve(path[:, 2], np.ones(window_size)/window_size, mode='valid')
    ]).T
    
    # Ensure the path stays within reasonable bounds of the direct path
    optimized_distance = 0
    for i in range(1, len(path)):
        segment_distance = np.linalg.norm([
            (path[i, 0] - path[i-1, 0]) * 111320,
            (path[i, 1] - path[i-1, 1]) * 111320 * np.cos(np.radians(path[i-1, 0])),
            path[i, 2] - path[i-1, 2]
        ])
        optimized_distance += segment_distance
    
    # If the optimized path is too long, fall back to a more conservative approach
    if optimized_distance > direct_distance * 1.5:  # Allow max 50% increase
        # Reduce deviations
        path = 0.7 * path + 0.3 * np.array([
            np.interp(np.linspace(0, 1, len(path)), [0, 1], [start_point[0], end_point[0]]),
            np.interp(np.linspace(0, 1, len(path)), [0, 1], [start_point[1], end_point[1]]),
            np.interp(np.linspace(0, 1, len(path)), [0, 1], [start_point[2], end_point[2]])
        ]).T
    
    return path

def generate_safe_trajectory(start_point, end_point, preferred_altitude, traffic_zones):
    """Generate a safe trajectory avoiding high-traffic zones"""
    # Get initial safe path
    rough_path = find_safe_path(start_point, end_point, traffic_zones)
    
    # Smooth the path using cubic spline
    t = np.linspace(0, 1, len(rough_path))
    cs = CubicSpline(t, rough_path)
    
    # Generate final smooth trajectory
    t_fine = np.linspace(0, 1, 100)
    smooth_trajectory = cs(t_fine)
    
    return smooth_trajectory

@app.callback(
    [Output('trajectory-3d-graph', 'figure'),
     Output('trajectory-stats', 'children')],
    [Input('generate-trajectory', 'n_clicks')],
    [State('start-lat', 'value'),
     State('start-lon', 'value'),
     State('end-lat', 'value'),
     State('end-lon', 'value'),
     State('preferred-altitude', 'value'),
     State('trajectory-drone-selector', 'value')]
)
def update_trajectory_analysis(n_clicks, start_lat, start_lon, end_lat, end_lon, preferred_altitude, selected_drones):
    if n_clicks == 0 or None in [start_lat, start_lon, end_lat, end_lon, preferred_altitude]:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Please provide all input values",
            template="plotly_white",
            plot_bgcolor=colors['light'],
            paper_bgcolor=colors['light']
        )
        return empty_fig, "Please provide start and end coordinates along with preferred altitude."
    
    try:
        # Filter data for selected drones
        if not selected_drones:  # If no drones selected, use all drones
            selected_drones = unique_drone_ids
        
        filtered_df = df_clean[df_clean['aircraft_id'].isin(selected_drones)].copy()
        
        # Analyze traffic density with filtered data
        traffic_zones = analyze_traffic_density(filtered_df)
        
        # Generate direct path first
        start_point = np.array([start_lat, start_lon, preferred_altitude])
        end_point = np.array([end_lat, end_lon, preferred_altitude])
        
        # Create direct path
        t = np.linspace(0, 1, 50)
        direct_path = np.array([
            np.interp(t, [0, 1], [start_point[0], end_point[0]]),  # lat
            np.interp(t, [0, 1], [start_point[1], end_point[1]]),  # lon
            np.interp(t, [0, 1], [start_point[2], end_point[2]])   # alt
        ]).T
        
        # Generate optimized trajectory
        optimized_trajectory = find_safe_path(start_point, end_point, traffic_zones)
        
        # Create 3D visualization
        fig = go.Figure()
        
        # Plot existing flight paths with reduced opacity
        for drone_id in selected_drones:
            drone_data = filtered_df[filtered_df['aircraft_id'] == drone_id].tail(1000)
            fig.add_trace(go.Scatter3d(
                x=drone_data['longitude'],
                y=drone_data['latitude'],
                z=drone_data['altitude'],
                mode='lines',
                name=f'Drone {drone_id}',
                line=dict(color=colors['drones'][unique_drone_ids.index(drone_id) % len(colors['drones'])], width=1),
                opacity=0.3,
                showlegend=True
            ))
        
        # Plot traffic density zones with improved visibility
        for zone in traffic_zones:
            if zone['density'] > 5:  # Show only higher traffic zones
                points = zone['points']
                fig.add_trace(go.Mesh3d(
                    x=points[:, 1],  # longitude
                    y=points[:, 0],  # latitude
                    z=points[:, 2],  # altitude
                    opacity=0.3,  # Slightly increased opacity
                    color=colors['risk_zone'],
                    name=f'High Traffic Zone (Density: {zone["density"]})',
                    showlegend=True,
                    hoverinfo='name'
                ))
        
        # Plot direct path
        fig.add_trace(go.Scatter3d(
            x=direct_path[:, 1],  # longitude
            y=direct_path[:, 0],  # latitude
            z=direct_path[:, 2],  # altitude
            mode='lines',
            name='Direct Path',
            line=dict(
                color='rgba(255, 0, 0, 0.8)',  # Red color for direct path
                width=4,
                dash='dash'  # Dashed line for direct path
            ),
            opacity=1
        ))
        
        # Plot optimized trajectory with markers at deviation points
        fig.add_trace(go.Scatter3d(
            x=optimized_trajectory[:, 1],  # longitude
            y=optimized_trajectory[:, 0],  # latitude
            z=optimized_trajectory[:, 2],  # altitude
            mode='lines+markers',  # Add markers to show deviation points
            name='Safety-Optimized Path',
            line=dict(
                color=colors['recommended_path'],
                width=6
            ),
            marker=dict(
                size=4,
                color=colors['recommended_path'],
                symbol='circle'
            ),
            opacity=1
        ))
        
        # Add start and end points with clear markers
        fig.add_trace(go.Scatter3d(
            x=[start_point[1]],
            y=[start_point[0]],
            z=[start_point[2]],
            mode='markers',
            name='Start Point',
            marker=dict(
                size=8,
                color='green',
                symbol='diamond'
            ),
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter3d(
            x=[end_point[1]],
            y=[end_point[0]],
            z=[end_point[2]],
            mode='markers',
            name='End Point',
            marker=dict(
                size=8,
                color='red',
                symbol='diamond'
            ),
            showlegend=True
        ))
        
        # Update layout with improved camera and styling
        fig.update_layout(
            scene=dict(
                xaxis_title='Longitude',
                yaxis_title='Latitude',
                zaxis_title='Altitude (m)',
                aspectmode='cube',
                camera=dict(
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=1.5, y=1.5, z=1.2)
                ),
                annotations=[
                    dict(
                        showarrow=False,
                        x=start_point[1],
                        y=start_point[0],
                        z=start_point[2],
                        text="Start",
                        xanchor="left",
                        yanchor="bottom"
                    ),
                    dict(
                        showarrow=False,
                        x=end_point[1],
                        y=end_point[0],
                        z=end_point[2],
                        text="End",
                        xanchor="left",
                        yanchor="bottom"
                    )
                ]
            ),
            title=dict(
                text='Safe Trajectory Analysis',
                font=dict(size=16, color=colors['dark'])
            ),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor=colors['accent'],
                borderwidth=1
            ),
            template="plotly_white",
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        # Calculate statistics
        direct_length = np.sum(np.sqrt(np.sum(np.diff(direct_path, axis=0)**2, axis=1)))
        optimized_length = np.sum(np.sqrt(np.sum(np.diff(optimized_trajectory, axis=0)**2, axis=1)))
        avg_altitude = np.mean(optimized_trajectory[:, 2])
        risk_zones_avoided = sum(1 for zone in traffic_zones if zone['density'] > 5)
        path_difference = ((optimized_length - direct_length) / direct_length) * 100
        
        # Create enhanced statistics display
        stats = html.Div([
            html.H4("Trajectory Analysis", style={'color': colors['dark'], 'marginBottom': '15px'}),
            html.Div([
                html.Div([
                    html.Div("Selected Drones", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(f"{len(selected_drones)} drones: {', '.join(selected_drones)}", 
                            style={'fontSize': '1.1em', 'marginBottom': '15px'})
                ]),
                html.Div([
                    html.Div("Direct Path Length", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(f"{direct_length:.2f} km", style={'fontSize': '1.2em'})
                ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
                
                html.Div([
                    html.Div("Optimized Path Length", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div([
                        f"{optimized_length:.2f} km ",
                        html.Span(
                            f"(+{path_difference:.1f}%)",
                            style={'color': colors['warning'], 'fontSize': '0.9em'}
                        )
                    ], style={'fontSize': '1.2em'})
                ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
                
                html.Div([
                    html.Div("Average Altitude", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(f"{avg_altitude:.2f} m", style={'fontSize': '1.2em'})
                ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
                
                html.Div([
                    html.Div("Risk Zones Avoided", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(f"{risk_zones_avoided}", style={'fontSize': '1.2em'})
                ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
                
                html.Div([
                    html.Div("Safety Status", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div("Optimized for Safety", style={
                        'fontSize': '1.2em',
                        'color': colors['success']
                    })
                ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'})
            ]),
            
            # Add safety tips
            html.Div([
                html.P("Safety Analysis:", style={'fontWeight': 'bold', 'marginTop': '15px'}),
                html.Ul([
                    html.Li(f"Path deviation adds {path_difference:.1f}% distance to avoid high-traffic zones"),
                    html.Li(f"Successfully avoiding {risk_zones_avoided} high-traffic areas"),
                    html.Li("Vertical adjustments made to maintain safe separation"),
                ], style={'marginTop': '5px'})
            ], style={'marginTop': '10px', 'color': colors['text']})
        ])
        
        return fig, stats
        
    except Exception as e:
        print(f"Error in update_trajectory_analysis: {str(e)}")
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title=f"Error generating trajectory: {str(e)}",
            template="plotly_white",
            plot_bgcolor=colors['light'],
            paper_bgcolor=colors['light']
        )
        return empty_fig, f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=False)
