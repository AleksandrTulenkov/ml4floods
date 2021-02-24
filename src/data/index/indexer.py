import os
import json
from dateutil import parser
import math
import logging

from src.data.index.geographic_index import GeographicIndex
from src.data.index.indexer_arg_parser import IndexerArgParser


LOGGER = logging.getLogger(__name__)

MASTER_PREFIX = "worldfloods/tiffimages"
METADATA_PREFIX = "meta"
PROVIDER_GEOTIFF_PREFIXES = ["S2", "L8", "gt"]
CLOUDMASK_PREFIX = "cloudprob"
FLOODMAP_PREFIX = "floodmaps"


def index_worldfloods(fs_prefix, out_path):
    idx = GeographicIndex()
    count = 0
    totalcount = 0
    for file in os.listdir(os.path.join(fs_prefix, MASTER_PREFIX, METADATA_PREFIX)):
        if file.endswith(".json"):
            totalcount += 1
            with open(os.path.join(fs_prefix, MASTER_PREFIX, METADATA_PREFIX, file), "r") as f:
                metadata = json.load(f)
    
            # Some metadata is corrupted -- full of NaN. Let's not even try to deal with those records for now.
            # These records also tend not to have bounds
            if "bounds" in metadata:
                bounds = metadata["bounds"]
                satdate = satdate = parser.parse(metadata["satellite date"])
                s2satdate = satdate
    
                # Gather up the relevant files and some basic time/date metadata from them
                relevant_files = []
                basename = os.path.splitext(file)[0]
    
                if "s2metadata" in metadata and len(metadata["s2metadata"]) == 1:
                    s2satdate = satdate = parser.parse(metadata["s2metadata"][0]["date_string"])
    
                if os.path.exists(os.path.join(fs_prefix, MASTER_PREFIX, FLOODMAP_PREFIX, basename+".shp")):
                    relevant_files.append({"type": "floodmap", "last_modified": satdate, "path": os.path.join(MASTER_PREFIX, FLOODMAP_PREFIX, basename+".shp")})
    
                if os.path.exists(os.path.join(fs_prefix, MASTER_PREFIX, CLOUDMASK_PREFIX, basename+".tif")):
                    relevant_files.append({"type": "cloudmask", "last_modified": satdate, "path": os.path.join(MASTER_PREFIX, CLOUDMASK_PREFIX, basename+".tif")})
    
                count += 1
                for sat_prefix in PROVIDER_GEOTIFF_PREFIXES:
                    sat_path = os.path.join(fs_prefix, MASTER_PREFIX, sat_prefix, basename+".tif")
                    if os.path.exists(sat_path):
                        relevant_files.append({"type": "satellite_image", "last_modified": s2satdate if sat_prefix == "S2" else satdate, "provider_id": sat_prefix, "path": os.path.join(MASTER_PREFIX, sat_prefix, basename+".tif")})
    
                # Add these relevant files to each 1-degree x 1-degree bin
                # Covered area represented in half-open intervals:
                # [min_lat, max_lat)
                # [min_lon, max_lon)
                min_lat = math.floor(bounds[1])
                min_lon = math.floor(bounds[0])
                max_lat = math.floor(bounds[3]+1)
                max_lon = math.floor(bounds[2]+1)
                for lat in range(min_lat, max_lat):
                    for lon in range(min_lon, max_lon):
                        idx.append_at_coords(lat, lon, relevant_files)
    
    LOGGER.info(f"{count} valid records indexed out of {totalcount}")
    
    idx.save_index(out_path)

if __name__ == "__main__":
    args = IndexerArgParser().parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)

    index_worldfloods(args.worldfloods_path, args.output_path)
