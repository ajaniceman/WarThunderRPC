'''
Module to store map metadata for lookup in the mapinfo module.
This file contains a dictionary where each key is a map name and its value
is a dictionary containing geographical data and perceptual hashes for that map.
'''

#region Map Data
# The 'maps' dictionary stores metadata for various War Thunder maps.
# Each map entry includes:
# - 'hashes': A list of perceptual hashes (hexadecimal strings) generated from map images.
#             These hashes are used to identify the current in-game map.
# - 'ULHC_lat': The estimated latitude of the map's Upper Left Hand Corner (ULHC) in decimal degrees.
#               This is a crucial reference point for converting in-game coordinates to real-world lat/lon.
# - 'ULHC_lon': The estimated longitude of the map's Upper Left Hand Corner (ULHC) in decimal degrees.
# - 'size_km': The approximate size of the map in kilometers (assuming a square map).
#              This is used for scaling in-game coordinates to real-world distances.
maps = {
    "Hangar": {
        "hashes": ["00183c0c18180000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 0.0
    },
    "Kursk": {
        "hashes": ["0707937f153ccc5d"],
        "ULHC_lat": 51.16278580067218,
        "ULHC_lon": 36.906235369488115,
        "size_km": 65
    },
    "Second Battle of El Alamein": {
        "hashes": ["000000c0f0ffffff", "7878fef6ffef80f0"],
        "ULHC_lat": 30.462785800672183,
        "ULHC_lon": 27.37730048853951,
        "size_km": 65
    },
    "Frozen Pass": {
        "hashes": ["000820e066cf9fff"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Berlin": {
        "hashes": ["00016000f3ffffb6", "5f0f071008808cff"],
        "ULHC_lat": 52.69241915403975,
        "ULHC_lon": 12.939497976797764,
        "size_km": 65
    },
    "Eastern Europe": {
        "hashes": ["7c3c1c0e2a0c1f0f"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Finland": {
        "hashes": ["fffe1c08081f1f3f", "1f0f1f7bf3f3bbf9"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "White Rock Fortress": {
        "hashes": ["8fc68480e6b6acc7"],
        "ULHC_lat": 52.37723024511663,
        "ULHC_lon": 24.130386051468452,
        "size_km": 65
    },
    "North Holland": {
        "hashes": ["f0f0e0e0e0f8f8fe", "00001317dffef0f0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Jungle": {
        "hashes": ["c0607e5e1b707e3c", "080c0700c0f0ff7f"],
        "ULHC_lat": -8.979060649367147,
        "ULHC_lon": 159.61888231748685,
        "size_km": 65
    },
    "Hurtgen": {
        "hashes": ["0000c0c0b3fbff3e"],
        "ULHC_lat": 50.95512512075716,
        "ULHC_lon": 5.878575498271389,
        "size_km": 65
    },
    "Battle of Hurtgen Forest": {
        "hashes": ["181a72fcc5e1c103"],
        "ULHC_lat": 50.95512512075716,
        "ULHC_lon": 5.878575498271389,
        "size_km": 65
    },
    "Ash River": {
        "hashes": ["80c48280c3dfbfff"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Carpathians": {
        "hashes": ["003cf9f3f0e2d22c", "0080e0703f8f3fff"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Kuban": {
        "hashes": ["fffeed614361e160", "f8f87f7f3f070300"],
        "ULHC_lat": 45.04056357844995,
        "ULHC_lon": 38.15663550630323,
        "size_km": 65
    },
    "Mozdok. Winter 1943": {
        "hashes": ["fffff3bf0f07008c"],
        "ULHC_lat": 43.74723024511662,
        "ULHC_lon": 45.530795428447014,
        "size_km": 65
    },
    "Mozdok": {
        "hashes": ["7d0d0c31b3030301", "000000f0f0f8ffff"],
        "ULHC_lat": 43.74723024511662,
        "ULHC_lon": 45.530795428447014,
        "size_km": 65
    },
    "Normandy": {
        "hashes": ["ff0340ffffff2000"],
        "ULHC_lat": 49.63227696246796,
        "ULHC_lon": -1.3594883491003418,
        "size_km": 65
    },
    "Fields of Poland": {
        "hashes": ["f0f0f0a2030f1f0f"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Poland": {
        "hashes": ["f0e0f0b2030f1f0f", "000040646eff7f7f"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Port Novorossiysk": {
        "hashes": ["fff3f8f0c0c0f0f8"],
        "ULHC_lat": 45.00567346614783,
        "ULHC_lon": 37.350655006295746,
        "size_km": 65
    },
    "Advance to the Rhine": {
        "hashes": ["e380a0c8c899ece6"],
        "ULHC_lat": 51.20370617772062,
        "ULHC_lon": 6.435754396363979,
        "size_km": 65
    },
    "Stalingrad": {
        "hashes": ["3f807efcfefcf0f1"],
        "ULHC_lat": 49.03954739312017,
        "ULHC_lon": 44.125799065790865,
        "size_km": 65
    },
    "Tunisia": {
        "hashes": ["eefcfe0000fefefe", "b8f8f0f0f030f8f8"],
        "ULHC_lat": 34.38385631810749,
        "ULHC_lon": 9.607620383816162,
        "size_km": 65
    },
    "Volokolamsk": {
        "hashes": ["f7e54d49e8d8fc3e", "bf3f879786100091"],
        "ULHC_lat": 56.28465547578633,
        "ULHC_lon": 35.53371105016213,
        "size_km": 65
    },
    "Sinai": {
        "hashes": ["f2f8ece2f0f8fcfe"],
        "ULHC_lat": 30.23374925858564,
        "ULHC_lon": 32.37627803962282,
        "size_km": 65
    },
    "Sands of Sinai": {
        "hashes": ["6020767717971b83"],
        "ULHC_lat": 30.23374925858564,
        "ULHC_lon": 32.37627803962282,
        "size_km": 65
    },
    "38th Parallel": {
        "hashes": ["2f07030080c1e3df", "7fe7970303170707"],
        "ULHC_lat": 38.70700365064681,
        "ULHC_lon": 127.39023242587562,
        "size_km": 65
    },
    "Abandoned Factory": {
        "hashes": ["ff1f3f0702060f1f", "3f2b7b1f015130ff"],
        "ULHC_lat": 57.66291098116433,
        "ULHC_lon": 42.45258058454457,
        "size_km": 65
    },
    "Ardennes": {
        "hashes": ["df60809061ffdbd0", "030f3ffcfcf080e3"],
        "ULHC_lat": 50.251285800672186,
        "ULHC_lon": 5.237050593588114,
        "size_km": 65
    },
    "Japan": {
        "hashes": ["e0e0c0c0c0cfffff", "0c00476130fcfd0d"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Fulda": {
        "hashes": ["083c1e7c7870f0c0", "c19110161f1f9fbf"],
        "ULHC_lat": 50.98906896351211,
        "ULHC_lon": 9.438324835920618,
        "size_km": 65
    },
    "Middle East": {
        "hashes": ["fcfefdff7e380001", "d000241c00c7f7ff"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Maginot Line": {
        "hashes": ["ef0f0f1606040800", "3f0f0384d071383f"],
        "ULHC_lat": 49.97091258566965,
        "ULHC_lon": 4.53954231640873,
        "size_km": 65
    },
    "Campania": {
        "hashes": ["00007e7e7e7e3c00", "3fffdf3f77000001"],
        "ULHC_lat": 40.99554413400551,
        "ULHC_lon": 14.322532826882213,
        "size_km": 65
    },
    "American Desert": {
        "hashes": ["fcfcfd9910befc0c", "9f3e5cd0e0b0121b"],
        "ULHC_lat": 37.19013831774728,
        "ULHC_lon": -111.84834368245951,
        "size_km": 65
    },
    "Vietnam": {
        "hashes": ["013e3c7cfefe7c08", "fefcfcf8d0c00000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Ground Zero": {
        "hashes": ["0ebcfe78f87c1e0c"],
        "ULHC_lat": 19.590322302910888,
        "ULHC_lon": 166.3231558227364,
        "size_km": 65
    },
    "Alaska": {
        "hashes": ["0c3efe78f87c1e0c", "133b19c024ef6206"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Cargo Port": {
        "hashes": ["00307c7c3c3c3c00", "f8f8f0f8f0fcfefe"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Britain": {
        "hashes": ["14f4fcfcf8000001"],
        "ULHC_lat": 51.41911138229066,
        "ULHC_lon": 0.7269576439621817,
        "size_km": 65
    },
    "Malta": {
        "hashes": ["182070381e1e0000"],
        "ULHC_lat": 36.23008394553646,
        "ULHC_lon": 14.02448607893447,
        "size_km": 65
    },
    "Peleliu": {
        "hashes": ["0b0f0e1c18182000"],
        "ULHC_lat": 7.3746069701216665,
        "ULHC_lon": 133.94223431827788,
        "size_km": 65
    },
    "Guadalcanal": {
        "hashes": ["080c2700c0f0ff7f"],
        "ULHC_lat": -9.01556441963102,
        "ULHC_lon": 159.74854533169756,
        "size_km": 65
    },
    "Iwo Jima": {
        "hashes": ["07c3181c18e0e370"],
        "ULHC_lat": 25.083745648448662,
        "ULHC_lon": 141.02666374065078,
        "size_km": 65
    },
    "Spain": {
        "hashes": ["e7efbfb6f0f0f0e0"],
        "ULHC_lat": 41.220061612629365,
        "ULHC_lon": 0.2981588394877504,
        "size_km": 65
    },
    "Khalkhin Gol": {
        "hashes": ["0781814169e7f0fb"],
        "ULHC_lat": 48.041953339619454,
        "ULHC_lon": 118.24492269637929,
        "size_km": 65
    },
    "New Guinea": {
        "hashes": ["0f0f0f6737030301"],
        "ULHC_lat": -9.134260168030261,
        "ULHC_lon": 146.94665506733256,
        "size_km": 65
    },
    "Ruhr": {
        "hashes": ["080503071f1f0f8f"],
        "ULHC_lat": 51.73829303094487,
        "ULHC_lon": 6.437537416826182,
        "size_km": 65
    },
    "Sicily": {
        "hashes": ["fcf8f0e0fcfefcfe"],
        "ULHC_lat": 37.62582130005829,
        "ULHC_lon": 14.575726231320882,
        "size_km": 65
    },
    "Mysterious Valley": {
        "hashes": ["00e1ffffc7277fef"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Bulge": {
        "hashes": ["0f6ffcf8fe781000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Korea": {
        "hashes": ["00c00cb88cbcfcff"],
        "ULHC_lat": 38.310264019718346,
        "ULHC_lon": 127.2747578040516,
        "size_km": 65
    },
    "Honolulu": {
        "hashes": ["70f8f8fe6f6f0200"],
        "ULHC_lat": 21.742180886911395,
        "ULHC_lon": -158.2681626706867,
        "size_km": 65
    },
    "Afghanistan": {
        "hashes": ["000018dc3c3fff7b"],
        "ULHC_lat": 35.22242668541464,
        "ULHC_lon": 68.95616436599424,
        "size_km": 65
    },
    "Smolensk": {
        "hashes": ["1f1f1c09117fe343", "1f1f1c09113fe303"],
        "ULHC_lat": 55.08537566230713,
        "ULHC_lon": 31.556597199003146,
        "size_km": 65
    },
    "African Canyon": {
        "hashes": ["fcfcd8e46c0e0080"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Gorge": {
        "hashes": ["ffc300000000e3ff"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Foothills": {
        "hashes": ["000000010383cfdf"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Cliffed Coast": {
        "hashes": ["fffc20c0d0c080e0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Alpine Meadows": {
        "hashes": ["3f9f47030363c7c4"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Wake Island": {
        "hashes": ["fffff9f8d8c0c000", "f7fef9f8d8c08000", "f7fff9f8d8c08000"],
        "ULHC_lat": 19.590322302910888,
        "ULHC_lon": 166.3231558227364,
        "size_km": 65
    },
    "European Province": {
        "hashes": ["fe7e73f701070301"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Defending Stalingrad": {
        "hashes": ["f8f8f8f0e0e0e0e0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Fire Arc": {
        "hashes": ["80c0f0f8d8fcf8f0", "0707d37f17bdecdd"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Fields of Normandy": {
        "hashes": ["c03c642113537176", "000003e6618fdfcf"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Sweden": {
        "hashes": ["003c7e7e7e7c3c00", "003876fe7e7e3c00"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Seversk-13": {
        "hashes": ["9f1b3efebe660090", "d38b88801c8081c7"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Red Desert": {
        "hashes": ["df81d9e0e0e981db"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Breslau": {
        "hashes": ["98883e3e3e0e0e8c", "7f3fef8787c3e3cd"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Spaceport": {
        "hashes": ["79c4dcf1e187e2e0", "3c9c5c33e044900a"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Aral Sea": {
        "hashes": ["fbffffc6c2c2c880", "fefefcf0e0e0e0e0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Sun City": {
        "hashes": ["f0f8f8e0c0e0f8f8", "f8f8f8f0f0f8f8f8"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Abandoned Town": {
        "hashes": ["c0f0fcfece604000", "3f1f0008c1e0e0e0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Pradesh": {
        "hashes": ["f3f7a282d3e3e3f9", "21070701011f1f5e"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Artic Polar Base": {
        "hashes": ["e4fcfcfedf1c2aef", "4608063e38c00009"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Golden Quarry": {
        "hashes": ["0f47c38008b88fe6", "80f1e7f003010fe0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Fields of Poland Winter": {
        "hashes": ["0f0f1fdde4e4f0f0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Maginot Line Winter": {
        "hashes": ["0f471b1f1f1f3f02"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Seversk 13 Winter": {
        "hashes": ["3f1ffcc1811f23f3"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Iberian Castle": {
        "hashes": ["ffffff7f3f1f0000", "ffff7f3e00000000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Test Site 2271": {
        "hashes": ["fee8c39b9b828000", "516b19800cc74206"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Flanders": {
        "hashes": ["fcfe5e1e1c0802c3", "0f0f0f0f0f8f87e3"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Kamchatka": {
        "hashes": ["c7cf133330307840"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Southeastern City": {
        "hashes": ["e1432f3c78200f7f"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Rocky Pillars": {
        "hashes": ["fcdec8e8b0000000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Rocky Canyon": {
        "hashes": ["decfc3c3a1f0fc7c"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Pyrenees": {
        "hashes": ["7f02f0fe0f008017"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Ladoga Winter 1941": {
        "hashes": ["c3c3c3c3ffffffff"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Falkalnd Islands": {
        "hashes": ["0000163f7f7c0000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Moscow": {
        "hashes": ["e8e020d0f880e07e"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Battle for Vietnam": {
        "hashes": ["7c7eff1f1e1c0800"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Attica": {
        "hashes": ["000c7c7ffffc2400", "fffede1e0e074300"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Golan Heights": {
        "hashes": ["07070f0f1f1f1f2f"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Bourbon Island": {
        "hashes": ["00183c3c3c180000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Western Europe": {
        "hashes": ["e08080050fcfefe7"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Hokkaido": {
        "hashes": ["080c1c7c70707000"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Laizhou Bay": {
        "hashes": ["00031371fbf0e8f0"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "City": {
        "hashes": ["079b8683c5c5c2c2"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Husky": {
        "hashes": ["fcf8f0e0fcfefcfe"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Korsun": {
        "hashes": ["e3c188a327f399bf"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
    "Battle for the Rhine": {
        "hashes": ["0787c7e3c3c0cbcf"],
        "ULHC_lat": 0.0,
        "ULHC_lon": 0.0,
        "size_km": 65
    },
}
#endregion
