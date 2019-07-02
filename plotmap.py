import pandas as pd
from base64 import b64encode
import folium
import branca
import json
from branca.element import MacroElement
from jinja2 import Template
import matplotlib.pyplot as plt
from grouped_layer_control import GroupedLayerControl
from branca.colormap import linear, LinearColormap
from folium import plugins
from geopy.geocoders import Nominatim

class BindColormap(MacroElement):
    def __init__(self, layer, colormap):
        super(BindColormap, self).__init__()
        self.layer = layer
        self.colormap = colormap
        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
            {{this._parent.get_name()}}.on('overlayadd', function (eventLayer) {
                if (eventLayer.layer == {{this.layer.get_name()}}) {
                    {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
                }});
            {{this._parent.get_name()}}.on('overlayremove', function (eventLayer) {
                if (eventLayer.layer == {{this.layer.get_name()}}) {
                    {{this.colormap.get_name()}}.svg[0][0].style.display = 'none';
                }});
        {% endmacro %}
        """)

class BaseMap():
    """Creates a base map to create and plot visualisations

    Parameters
    ----------
    data : pandas dataframe or path to CSV file
        Dataset that would be used for creating the map.

    shapefile : path to a GeoJSON file
        Shapefile for plotting on a map

    Examples
    --------
    >>> map1 = BaseMap()
    >>> map2 = BaseMap(shapefile = 'data/country3.0.geojson' )
    """

    def __init__(self, data = None, shapefile = None):
        self.map = folium.Map(location = [2,-2], zoom_start = 3)
        self.feature_groups = {}

        # Gets FB data
        if type(data) == str:
            self.df = pd.read_csv(data)
        else:
            self.df = data

        # Gets map data
        if shapefile is None:
            pass
        elif shapefile.lower().endswith('.geojson'):
            self.geodata = json.load(open(shapefile))
        else:
            print("Currently we have support only for GeoJSON files. Please enter a GeoJson file.")

    def groupedLayerControl(self, radio = []):

        """Creates a grouped layer control.

        Parameters
        --------
        radio : List of groups that should have mutually exclusive items.

        Examples
        --------
        >>> map.groupedLayerControl()

        """
        for i in self.feature_groups.keys():
            if i in radio:
                self.feature_groups[i]['None'] = folium.map.FeatureGroup(name='None', show=False).add_to(self.map)
        GroupedLayerControl({}, self.feature_groups, radio).add_to(self.map)

    def getMap(self):
        """Returns a folium map object.

        Returns
        --------
        folium map object

        Examples
        --------
        >>> bmap.getMap()

        """
        return self.map


    def createGroup(self, name):
        self.feature_groups[name] = {}


class Geojson():

    """Creates a Choropleth map.

    Parameters
    ----------
    baseMap : A BaseMap object is given to the function

    name : Name of the Choropleth map being created
    
    country: place name (does not have to be a country name)

    data : pandas dataframe or path to CSV file
        Dataset that would be used for creating the map.

    shapefile : path to a GeoJSON file
        Shapefile for plotting on a map
        
    locationcol: the name of column that cotains location names
    
    total: the name of column which tells the total number of people

    Returns
    -------
    geojson object

    Examples
    --------
    >>> Geo = Geojson(basemap, 'Choropleth', shapefile = 'geodata/city3.0.geojson')

    """

    def __init__(self, baseMap, feature_group, name, country=None, data = None, shapefile = None, locationcol = 'Location', total = None):
        self.baseMap = baseMap
        self.name = name
        self.vdict, self.vdict2 = {}, {}
        self.column1, self.column2 = None, None
        self.colormap = None
        self.colormap2 = None
        self.plotcolumns, self.plotlabels = [],[]
        self.valuecolumns, self.valuestring = [], []
        self.absolutecolumns, self.absolutestring = [], []
        self.locationcol = locationcol
        self.key = 'name'
        self.feature_group = feature_group
        self.total_number = total
        self.country = country

        # Gets Facebook data
        if data is None and self.baseMap is not None:
            self.df = self.baseMap.df
        elif type(data) == str:
            self.df = pd.read_csv(data)
        else:
            self.df = data

        if shapefile == None:
            self.geodata = self.baseMap.geodata
        else:
            self.geodata = json.load(open(shapefile))
        self.baseMap.feature_groups[self.feature_group][self.name] = folium.map.FeatureGroup(name=name, show=False).add_to(self.baseMap.map)

    """Creates a color map

    Parameters
    ----------
    column1 : name of the column which need to be represented on the map

    Examples
    --------
    >>> g.colorMap('Total_mau')

    """
    def colorMap(self,column1):
        template = """
        {% macro html(this, kwargs) %}

        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">
          
          <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
          <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
          
          <script>
          $( function() {
            $( "#maplegend" ).draggable({
                            start: function (event, ui) {
                                $(this).css({
                                    right: "auto",
                                    top: "auto",
                                    bottom: "auto"
                                });
                            }
                        });
        });

          </script>
        </head>
        <body>

         
        <div id='maplegend' class='maplegend' 
            style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8);
             border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px;'>

        <div class='legend-title'>Migrants From Each Country</div>
        <div class='legend-scale'>
          <ul class='legend-labels'>
            <li><span style='background:#fee5d9;opacity:1;'></span>1,001 to 10,001</li>
            <li><span style='background:#fcae91;opacity:1;'></span>10,001 to 20,001</li>
            <li><span style='background:#fb6a4a;opacity:1;'></span>20,001 to 50,001</li>
            <li><span style='background:#de2d26;opacity:1;'></span>50,001 to 100,001</li>
            <li><span style='background:#a50f15;opacity:1;'></span> > 100,001</li>
            <li><span style='background:#000000;opacity:1;'></span>""" + self.country + """</li>

          </ul>
        </div>
        </div>
         
        </body>
        </html>

        <style type='text/css'>
          .maplegend .legend-title {
            text-align: left;
            margin-bottom: 5px;
            font-weight: bold;
            font-size: 90%;
            }
          .maplegend .legend-scale ul {
            margin: 0;
            margin-bottom: 5px;
            padding: 0;
            float: left;
            list-style: none;
            }
          .maplegend .legend-scale ul li {
            font-size: 80%;
            list-style: none;
            margin-left: 0;
            line-height: 18px;
            margin-bottom: 2px;
            }
          .maplegend ul.legend-labels li span {
            display: block;
            float: left;
            height: 16px;
            width: 30px;
            margin-right: 5px;
            margin-left: 0;
            border: 1px solid #999;
            }
          .maplegend .legend-source {
            font-size: 80%;
            color: #777;
            clear: both;
            }
          .maplegend a {
            color: #777;
            }
        </style>
        {% endmacro %}"""

        macro = MacroElement()
        tm=Template(template)
        macro._template = tm
        self.macro=macro
        self.vdict = self.df.set_index(self.locationcol)[column1] 
          
    """Creates the Choropleth map.
    Parameters
    ----------
    key: key name on geojson file

    Examples
    --------
    >>> geo.createMap()

    """
    def createMap(self, key = 'name'):
        self.key = key
        folium.GeoJson(self.geodata, 
                       style_function=lambda feature: {
                         'fillColor': 'white' if feature['properties'][self.key] not in self.vdict
                         else 'black' if feature['properties'][self.key] == self.country
                        else 'grey' if self.vdict[feature['properties'][self.key]]<1001
                        else '#fee5d9' if self.vdict[feature['properties'][self.key]]<10001
                        else '#fcae91' if self.vdict[feature['properties'][self.key]]<20001
                        else '#fb6a4a' if self.vdict[feature['properties'][self.key]]<50001
                        else '#de2d26' if self.vdict[feature['properties'][self.key]]<100001
                        else '#a50f15', 
      'color': 'black',
      'weight': 2 if (self.column2 != None) else 0.5,
      'fillOpacity': 0 if feature['properties'][self.key] not in self.vdict
                    else 0 if self.vdict[feature['properties'][self.key]]<1001
                    else 1,
      'opacity': 0 if feature['properties'][self.key] not in self.vdict
                else 0 if self.vdict[feature['properties'][self.key]]<1001
                else 1
      },
       tooltip=folium.features.GeoJsonTooltip(fields=[self.key],
                                          labels=False,
                                          sticky=False)).add_to(self.baseMap.feature_groups[self.feature_group][self.name])
        self.macro.add_to(self.baseMap.feature_groups[self.feature_group][self.name])
        
    def colorMap_Linear(self, column1, column2 = None, threshold_min1 = None, threshold_min2 = None, 
                  threshold_max1 = None, threshold_max2= None, method='linear'):
        
        """Creates a colormap for the Choropleth map.

        Parameters
        ----------
        column1 : Attribute that specifies the fill colour of the Choropleth map

        column2 : Attribute that spceifies the border colour of the Choropleth map

        Examples
        --------
        >>> geo.colorMap('Population', 'PopDensity')

        """
        
        if threshold_min1 == None:
            threshold_min1 = self.df[column1].min()
        if threshold_max1 == None:
            threshold_max1 = self.df[column1].max()
        self.column1 = column1
        self.colormap = LinearColormap(['#3f372f', '#62c1a6', '#1b425e','#bbf9d9', '#ffffff'],
                                       vmin=self.df[self.df[column1] >= threshold_min1][column1].min(),
                                       vmax=self.df[self.df[column1] <= threshold_max1][column1].max()).to_step(
            data=self.df[self.df[column1] <= threshold_max1][self.df[column1] >= 0][column1], n=5, method=method)
        self.vdict = self.df[self.df[column1] <= threshold_max1][self.df[column1] >= threshold_min1].set_index(self.locationcol)[column1]
        self.baseMap.map.add_child(self.colormap)        
        self.baseMap.map.add_child(BindColormap(self.baseMap.feature_groups[self.feature_group][self.name], self.colormap))
        
        if column2 == None:
            self.colormap2 = None
        else:
            if threshold_min2 == None:
                threshold_min2 = self.df[column2].min()
            if threshold_max2 == None:
                threshold_max2 = self.df[column2].max()
            self.column2 = column2
            self.colormap2=LinearColormap(['#3f372f', '#62c1a6', '#1b425e','#bbf9d9', '#ffffff'],vmin=self.df[self.df[column2] >= threshold_min2][column2].min(),vmax=self.df[self.df[column2] <= threshold_max2][column2].max()).to_step(data=self.df[self.df[column2] <= threshold_max2][self.df[column2] >= 0][column2], n=5, method=method)
            self.vdict2 = self.df[self.df[column2] <= threshold_max2][self.df[column2] >= threshold_min2].set_index(self.locationcol)[column2]
            self.baseMap.map.add_child(self.colormap2)
            self.baseMap.map.add_child(BindColormap(self.baseMap.feature_groups[self.feature_group][self.name], self.colormap2))

    def createMap_Linear(self, key = 'name'):
        
        """Creates the Choropleth map.
        Parameters
        ----------
        key: key name on geojson file

        Examples
        --------
        >>> geo.createMap_Linear()

        """
        self.key = key
        folium.GeoJson(self.geodata, 
                       style_function=lambda feature: {
        'fillColor': (self.colormap(self.vdict[feature['properties'][self.key]]) if feature['properties'][self.key] in self.vdict else 'grey') if ~(self.column1 == None) else 'black',
      'color': (self.colormap2(self.vdict2[feature['properties'][self.key]]) if feature['properties'][self.key] in self.vdict2 else 'grey') if ~(self.column2 == None) else 'black',
      'weight': 2 if (self.column2 != None) else 0.5,
      'fillOpacity': 1 if feature['properties'][self.key] in self.vdict else 0},
       tooltip=folium.features.GeoJsonTooltip(fields=[self.key],
                                          labels=False,
                                          sticky=False)).add_to(self.baseMap.feature_groups[self.feature_group][self.name])
        

    def addValue(self, columns, string):

        """Takes input for the information to be displayed in the information box as text.

        Parameters
        ----------
        columns : The column value to be displayed

        string : The string following the value

        Examples
        --------
        >>> geo.addValue("ven/pop", " of the population are Venezuelans.")
        >>> geo.addValue("ven/migrants", " of the migrants are Venezuelans.")

            """
        self.valuecolumns.append(columns)
        self.valuestring.append(string)

    def addAbsolute(self, columns, string):

        """Takes input for the information to be displayed in the information box as text.

        Parameters
        ----------
        columns : The column value to be displayed

        string : The string following the value

        Examples
        --------
        >>> geo.addAbsolute("pop", " number of people who are Venezuelans.")
        >>> geo.addAbsolute("migrants", " number of migrants who are Venezuelans.")

            """
        self.absolutecolumns.append(columns)
        self.absolutestring.append(string)

    def createPlots(self, columns, labels):

        """Takes input for the plots to be displayed in the information box.

        Parameters
        ----------
        columns : A list of column names used to create the pie chart.

        labels: A list of labels corresponding to the column values for the pie chart.

        Examples
        --------
        >>> geo.createPlots(["Male_mau", "Female_mau"], ['Men', 'Women'])
        
        """

        self.plotcolumns.append(columns)
        self.plotlabels.append(labels)

    def copyInfoBox(self, geojson):

        """Copies the structure of information box created for one geojson object to another.

        Parameters
        ----------
        geojson : A geojson object whose information box's structure is to be copied.

        Examples
        --------
        >>> geo.copyInfoBox(geojson1)

        """
        # TODO: you are probably missing .copy() function here.
        self.valuecolumns = geojson.valuecolumns
        self.valuestring = geojson.valuestring
        self.absolutecolumns=geojson.absolutecolumns
        self.absolutestring=geojson.absolutestring
        self.plotcolumns = geojson.plotcolumns
        self.plotlabels = geojson.plotlabels

    def addInfoBox(self):

        """Adds information box to the choropleth map as a pop up.

        Examples
        --------
        >>> geo.addInfoBox()

        """
        # ToDo: probably needs to check if self.key is in feature['properties']

        for feature in self.geodata['features']:
            # Gets a row in the df for a given location and transforms it into a series
            s = self.df[self.df[self.locationcol] == feature['properties'][self.key]].squeeze()

            if not s.empty:
#                 if self.vdict[feature['properties'][self.key]]>=1001:
                    html = "<center><h2 style='font-family: Arial, Helvetica, sans-serif;'>" + feature['properties'][self.key] + "</h2></center><center>"
                    for i in range(len(self.absolutecolumns)):
                        html += "<h4 style='font-family: Arial, Helvetica, sans-serif;'>"+str(round(s[self.absolutecolumns[i]], 2)) + self.absolutestring[i] + "</h4>"

                    for i in range(len(self.valuecolumns)):
                        total = s[self.valuecolumns[i]].sum()
                        value = s[self.valuecolumns[i][0]]
                        html += "<h4 style='font-family: Arial, Helvetica, sans-serif;'>" + str(round(value/total*100., 2)) + "%" + self.valuestring[i] + "</h4>"

                    a = self.df[self.df[self.locationcol]== feature['properties'][self.key]]
                    encodedlist = []
                    for i in range(len(self.plotcolumns)):
                        fig1, ax1 = plt.subplots(figsize=(5,3))
                        ax1.pie([a.loc[(a.index)[0],j] for j in self.plotcolumns[i]], labels=self.plotlabels[i], autopct='%1.1f%%', shadow=True, startangle=90)
                        plt.savefig('myfig.png', transparent = True)
                        encoded = b64encode(open('myfig.png', 'rb').read()).decode()
                        encodedlist.append(encoded)
                        html += '<img align="middle" src="data:image/png;base64,{}">'
                  
                    html += '</center>'

                    geo = folium.GeoJson(feature['geometry'],
                           style_function = lambda feature: { 'weight': 0,'fillOpacity': 0},
                            tooltip = feature['properties'][self.key])

                    iframe = branca.element.IFrame(html=html.format(*encodedlist), width=400, height=400)
                    folium.Popup(iframe).add_to(geo)
                    geo.add_to(self.baseMap.feature_groups[self.feature_group][self.name])

class InterestingFacts():
    """Creates a map with icons showing interesting facts

    Parameters
    ----------
    baseMap : A baseMap object is given to the function

    feature_group: name for feature_group dict

    name : Name of the feature group which needs to be added to a dict

    location: column name for location

    data : pandas dataframe or path to CSV file
        Dataset that would be used for creating the map.

    Examples
    --------
    >>> f= interestingFacts(basemap, 'City', 'name', location, data = df)

    """
    def __init__(self, basemap, feature_group, name, locationcol = 'Location', data = 'None'):
        self.basemap = basemap
        self.name = name
        self.Loc= []
        self.tdict, self.pdict, self.pidict, self.hdict, self.cdict={}, {}, {}, {}, {}
        self.feature_group = feature_group
        self.locationcol=locationcol
        if type(data)==str:
            if data == 'None':
                self.df=self.basemap.df
            elif data[-4:]=='.csv':
                self.df = pd.read_csv('data')
            else:
                print("Enter path to a csv file.")
        else:
            self.df = data
        self.basemap.feature_groups[self.feature_group][self.name] = folium.map.FeatureGroup(name=self.name, show=True).add_to(self.basemap.map)


    def addFacts(self, array, labels, icon_map, icon_pop):
        """Creates icons on map

        Parameters
        ----------
        array : List of column name
        label : Tuple of label name
        icon_map : the icon shown on map
        icon_pop : pop up icon

        Examples
        --------
        >>> f.addFacts(['Total_mau','Other_mau', 'iOS_mau', 'Android_mau'], ('Other', 'iOS', 'Android'),'phone.png', 'myfig.png')

        """
        df=self.df
        totalname=array[0]
        array=array[1:]
        for i in range(len(array)):
            df[array[i]+totalname]=df[array[i]]/df[totalname]
        for i in range(len(array)):
            arr = [0]*len(array)
            name=array[i]+totalname
            a = df.loc[df[name].idxmax(axis=1)]
            for j in range(len(array)):
                arr[j]=a[array[j]]
            fig1, ax1 = plt.subplots(figsize=(1.8,1.8))
            ax1.pie(arr, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
            plt.savefig('myfig.png', transparent = True)
            html1 = '<center><img align="middle" src="data:image/png;base64,{}"></center>'
            encoded = b64encode(open(icon_pop, 'rb').read()).decode()
            encpie = b64encode(open('myfig.png', 'rb').read()).decode()
            ic = icon_map
            l = a[self.locationcol]
            latlong=a['LatLong']
            if l not in self.Loc:
                self.Loc.append(l)
                self.pdict[l], self.hdict[l],self.tdict[l], self.pidict[l], self.cdict[l] = '<h4><center>' + l +'</center></h4>', '', [], [], 0
                self.tdict[l].append(encoded)
                self.pdict[l] += '<hr><center><p style="padding:0px 10px 0px 10px">'+ l
                self.hdict[l] += html1
            self.pidict[l].append(encpie)
            self.cdict[l]+=1
            string = " highest percentage of "+ labels[i]+"."
            self.pdict[l] += ' has the'+string+'</p></center><center><img align="middle" src="data:image/png;base64,{}"></center>'
            iframe = branca.element.IFrame(html=self.pdict[l].format(*self.pidict[l]), width=400, height = 220 + self.cdict[l]* 50)
            folium.Marker([latlong.split(",")[0], latlong.split(",")[1]], popup = folium.Popup(iframe), icon = folium.features.CustomIcon(ic,icon_size=(28, 30)),tooltip=self.hdict[l].format(*self.tdict[l]) ).add_to(self.basemap.feature_groups[self.feature_group][self.name])
    
    def getLatLong(self, name):
        l = Nominatim(user_agent="my-application").geocode(name)
        if (l==None):
            return "%.2f, %.2f" % (0, 0)
        return "%.2f, %.2f" % (l.latitude, l.longitude)
    
    def LatLong(self, csv_name):
        self.df["LatLong"] = self.df[self.locationcol].apply(lambda x: getLatLong(x))
        self.df.to_csv(csv_name, index=False)
