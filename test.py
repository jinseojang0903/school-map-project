import pandas as pd
import folium
import requests
from folium.plugins import MarkerCluster
from flask import Flask, render_template, request, jsonify
from geopy.distance import geodesic
import os
from flask import send_from_directory
import json

app = Flask(__name__, template_folder="frontend", static_folder="frontend") #main.js, index.html 들어있는 폴더 이름 frontend

CSV_PATH = "./데이터/주소위도경도.csv"
HIGHWAY_CSV_PATH = "./데이터/고속도로출입시설.csv"

if not os.path.exists(CSV_PATH):
    print(
        f"오류: '{CSV_PATH}' 파일을 찾을 수 없습니다. 스크립트와 같은 디렉토리에 '데이터' 폴더를 만들고 CSV 파일을 넣어주세요."
    )
    exit()
if not os.path.exists(HIGHWAY_CSV_PATH):
    print(f"오류: '{HIGHWAY_CSV_PATH}' 파일을 찾을 수 없습니다.")
    exit()

LAT_COL, LON_COL, POP_COL, RANK_COL = "위도", "경도", "폐교명", "점수 순위"
H_NAME_COL, H_LAT_COL, H_LON_COL = "IC/JC명", "위도", "경도"

REST_API_KEY = os.environ.get("KAKAO_API_KEY", "c6167fc9bb70ca9ea487094d849bb1f5")
SEARCH_RADIUS = 3000  #검색범위:3km

# 카테고리 코드 매핑
CATEGORY_MAP = {
    "restaurants": "FD6",
    "conveniences": "CS2",
    "cafes": "CE7",
    "hospitals": "HP8",
    "gncStations": "OL7",
    "accommodations": "AD5",
}

SCORE_COLUMN_MAP = {
    "hospitals": "병원 점수",
    "conveniences": "편의점 점수",
    "cafes": "카페 점수",
    "restaurants": "음식점 점수",
    "gncStations": "주유소 점수",
    "accommodations": "숙박시설 점수",
}


def load_csv_data(path, lat_col, lon_col):
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949")
    df = df.dropna(subset=[lat_col, lon_col]).astype({lat_col: float, lon_col: float})
    return df


df = load_csv_data(CSV_PATH, LAT_COL, LON_COL)
df_highway = load_csv_data(HIGHWAY_CSV_PATH, H_LAT_COL, H_LON_COL)

total_school_count = len(df)

CUSTOM_JS = """
cnt = 0;
const MIN_ZOOM_LEVEL = 8;
let currentAbortController = null;

window.onload = function () {
    const lightIconUrls = { 
        'hospitals': "/frontend/icons/hospital.png",
        'conveniences': "/frontend/icons/conveniences.png",
        'cafes': "/frontend/icons/cafes.png",
        'restaurants': "/frontend/icons/restaurant.png",
        'gncStations': "/frontend/icons/gas.png",
        'accommodations': "/frontend/icons/hotel.png",
        'highway': "/frontend/icons/highway.png",
        'default': "/frontend/icons/highway.png" 
    };
    const darkIconUrls = {
        'cafes': "/frontend/icons/cafesw.png", 
        'gncStations': "/frontend/icons/gasw.png",
        'accommodations': "/frontend/icons/hotelw.png", 
        'highway': "/frontend/icons/highwayw.png",
        'default': "/frontend/icons/highwayw.png",
        'hospitals': "/frontend/icons/hospital.png",
        'conveniences': "/frontend/icons/conveniences.png",
        'restaurants': "/frontend/icons/restaurant.png"
    };
    const isDarkMode = new URLSearchParams(window.location.search).get('dark_mode') === 'true';

    const mapElem = document.querySelector('.folium-map');
    if (!mapElem) return;

    if (!window._mainMap) {
        for (const key in window) {
            if (window[key] && typeof window[key].eachLayer === 'function') {
                window._mainMap = window[key];
                break;
            }
        }
    }

    if (window._mainMap) {
        const facilityLayerGroup = L.layerGroup().addTo(window._mainMap);
        const routeLayerGroup = L.layerGroup().addTo(window._mainMap);
        
        const light_color_arr = ['red', 'blue', 'green'];
        const dark_color_arr = ['#FFD700', '#00FFFF', '#FF00FF'];
        const color_arr = isDarkMode ? dark_color_arr : light_color_arr;

        window._mainMap.on('zoomend', function() {
            const currentZoom = window._mainMap.getZoom();
            if (currentZoom < MIN_ZOOM_LEVEL) {
                window._mainMap.setZoom(MIN_ZOOM_LEVEL);
            }
        });

        function createCustomIcon(category) {
            const iconUrls = isDarkMode ? darkIconUrls : lightIconUrls;
            
            return L.icon({ 
                iconUrl: iconUrls[category] || iconUrls.default, 
                iconSize: [32, 32], 
                iconAnchor: [16, 32], 
                popupAnchor: [0, -32] 
            });
        }
        
        function addMarker(lat, lon, name, category, isFacility, address = null, phone = null) {
            let popupText = `<b>${name}</b>`;
            if (address) popupText += `<br>📍 ${address}`;
            if (phone) popupText += `<br>📞 ${phone}`;
            const marker = L.marker([lat, lon], { icon: createCustomIcon(category), isFacilityMarker: true });
            marker.bindPopup(popupText).addTo(facilityLayerGroup);
        }

        function drawRoute(fromLat, fromLon, toLat, toLon, controller) {
             const url = `/route?from_lat=${fromLat}&from_lon=${fromLon}&to_lat=${toLat}&to_lon=${toLon}`;
            fetch(url, { signal: controller.signal })  // ✅ 연결
                .then(res => res.json())
                .then(result => {
                    if (result.route) {
                        cnt += 1;
                        const polyline = L.polyline(result.route, { color: color_arr[(cnt - 1) % 3], weight: 10, opacity: 0.7 });
                        polyline.addTo(routeLayerGroup);
                    }
                })
                .catch(err => {
                    if (err.name === 'AbortError') {
                        console.warn("🚫 이전 요청 중단됨");
                    } else {
                        console.error("❌ 경로 요청 실패:", err);
                    }
                });
        }

        function resetAllRoads() { routeLayerGroup.clearLayers(); cnt = 0; }

        window._mainMap.on('popupopen', function(e){
            const clickedLayer = e.popup._source;
            const isFacilityClick = clickedLayer.options.isFacilityMarker || false;
            
            if (!isFacilityClick) {
                if (currentAbortController) {
                    currentAbortController.abort();
                }
                currentAbortController = new AbortController();
            }
            
            if (!isFacilityClick) {
                const popupElement = e.popup.getElement();
                const schoolDataElement = popupElement.querySelector('.school-data');
                
                if (schoolDataElement) {
                    try {
                        const schoolData = JSON.parse(schoolDataElement.textContent);
                        
                        facilityLayerGroup.clearLayers();
                        resetAllRoads();
                        const {lat, lng} = e.popup._latlng;
                        const selectedFacilities = Array.from(window.parent.document.querySelectorAll('input[name="facility"]:checked')).map(cb => cb.value).join(',');
                        let fetchUrl = `/nearby?lat=${lat}&lon=${lng}&selected=${selectedFacilities}`;

                        fetch(fetchUrl, { signal: currentAbortController.signal })
                            .then(response => response.json())
                            .then(data => {
                                data.restaurants.forEach(o => addMarker(o.lat, o.lon, o.name, 'restaurants', true, o.address, o.phone));
                                data.hospitals.forEach(o => addMarker(o.lat, o.lon, o.name, 'hospitals', true, o.address, o.phone));
                                data.conveniences.forEach(o => addMarker(o.lat, o.lon, o.name, 'conveniences', true, o.address, o.phone));
                                data.cafes.forEach(o => addMarker(o.lat, o.lon, o.name, 'cafes', true, o.address, o.phone));
                                data.gncStations.forEach(o => addMarker(o.lat, o.lon, o.name, 'gncStations', true, o.address, o.phone));
                                data.accommodations.forEach(o => addMarker(o.lat, o.lon, o.name, 'accommodations', true, o.address, o.phone));
                                if (data.highways && data.highways.length > 0) {
                                    data.highways.forEach(o => { const popupText = `${o.name}<br><b>거리: ${o.distance_km.toFixed(2)} km</b>`;
                                    addMarker(o.lat, o.lon, popupText, 'highway');
                                    drawRoute(lat, lng, o.lat, o.lon, currentAbortController);
                                    });
                                }

                                schoolData.nearest_highways = data.highways || [];
                                window.parent.showSchoolInfoPanel(schoolData);
                            })
                             .catch(error => {
                                if (error.name === 'AbortError') {
                                    console.warn("🚫 fetch 요청이 중단됨");
                                } else {
                                    console.error('Fetch Error:', error);
                                }
                                window.parent.showSchoolInfoPanel(schoolData);
                                window._mainMap.closePopup(e.popup);
                            });
                    } catch (error) {
                        console.error("❌ 데이터 파싱 또는 API 호출 중 오류 발생:", error);
                    }
                } else {
                    console.error("❗️'.school-data' 요소를 팝업에서 찾지 못했습니다.");
                }
            }
        });
    } else {
        console.error("🛑 지도 객체(map object)를 찾을 수 없습니다.");
    }

    // --- [변경점 3] 왼쪽 패널 아이콘 변경 로직도 두 객체를 사용하도록 수정 ---
    const panel1 = document.getElementById('info-box-1');
    if (panel1) {
        // lightIconUrls의 키(key)들을 가져와서 반복
        Object.keys(lightIconUrls).forEach(value => {
            if (value === 'default') return; // default는 패널에 없으므로 건너뜀
            
            const input = panel1.querySelector(`input[value="${value}"]`);
            if (input) {
                const label = input.closest('label');
                if (label) {
                    const img = label.querySelector('img');
                    if (img) {
                        // 다크모드 여부에 따라 사용할 객체에서 아이콘 경로를 가져옴
                        const iconPath = isDarkMode ? darkIconUrls[value] : lightIconUrls[value];
                        img.src = iconPath;
                    }
                }
            }
        });
    }
};
"""


# ── Flask 서버 ───────────────────────────────
def kakao_search(lat, lon, code, pages=3):
    """카카오 API를 통해 여러 페이지의 장소 정보를 검색하는 함수"""
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {REST_API_KEY}"}
    all_results = []
    unique_places = set()

    for page in range(1, pages + 1):
        params = {
            "category_group_code": code,
            "x": lon,
            "y": lat,
            "radius": SEARCH_RADIUS,
            "size": 15,
            "page": page,
        }
        try:
            r = requests.get(url, headers=headers, params=params, timeout=3)
            if r.status_code != 200:
                print(f"Kakao error (page: {page}): {r.status_code} {r.text}")
                break
            data = r.json()
            documents = data.get("documents", [])
            for d in documents:
                place_id = d.get("id")
                if place_id not in unique_places:
                    unique_places.add(place_id)
                    all_results.append(
                        {
                            "name": d["place_name"],
                            "lat": float(d["y"]),
                            "lon": float(d["x"]),
                            "address": d.get("road_address_name", "주소 없음"),
                            "phone": d.get("phone", "번호 없음"),
                        }
                    )
            if data.get("meta", {}).get("is_end", True):
                break
        except Exception as e:
            print(f"Kakao request 요청 실패 (page: {page}):", e)
            break
    return all_results


@app.route("/")
def index():
    is_dark_mode = request.args.get("dark_mode") == "true"
    center = [34.5, 127]
    map_tiles = "cartodbdarkmatter" if is_dark_mode else "CartoDB positron"
    m = folium.Map(location=center, zoom_start=9, tiles=map_tiles, zoom_control=False)

    m.get_name = lambda: "map"
    cluster = MarkerCluster().add_to(m)

    for _, r in df.iterrows():
        school_info = {
            "name": r.get("폐교명"),
            "address": r.get("주소", "정보 없음"),
            "land_size": r.get("토지규모", "정보 없음"),
            "building_size": r.get("건물규모", "정보 없음"),
            "total_price": r.get("총 금액", "정보 없음"),
            "current_status": r.get("현재 상태", "정보 없음"),
            "nearest_highways": [],  # 이 부분은 이제 main.js에서 채움
            "ranks": {
                "restaurants": r.get("음식점 점수", 0),
                "conveniences": r.get("편의점 점수", 0),
                "cafes": r.get("카페 점수", 0),
                "hospitals": r.get("병원 점수", 0),
                "gas_stations": r.get("주유소 점수", 0),
                "accommodations": r.get("숙박시설 점수", 0),
            },
            "counts": {
                "restaurants": r.get("음식점 수", 0),
                "conveniences": r.get("편의점 수", 0),
                "cafes": r.get("카페 수", 0),
                "hospitals": r.get("병원 수", 0),
                "gas_stations": r.get("주유소 수", 0),
                "accommodations": r.get("숙박시설 수", 0),
            },
            "total_count": total_school_count,
        }
        school_info_json = json.dumps(school_info, ensure_ascii=False)

        popup_html = f"""
            <div class="school-data" style="display: none;">{school_info_json}</div>
            <b>{school_info['name']}</b><br>
        """
        popup = folium.Popup(popup_html, max_width=300)

        icon_image_path="frontend/icons/school.png"

        custom_icon = folium.CustomIcon(
            icon_image=icon_image_path,
            icon_size=(30, 30),
            icon_anchor=(15,30),
            popup_anchor=(0,-30)
        )
        folium.Marker(
            [r[LAT_COL], r[LON_COL]],
            popup=popup,
            icon=custom_icon
        ).add_to(cluster)

    # 초기 TOP 5는 '점수 순위'를 기준으로 계산
    top_5_schools = df.sort_values(by=RANK_COL, ascending=True).head(5)
    top_5_list = top_5_schools[[POP_COL, LAT_COL, LON_COL]].to_dict(orient="records")

    all_schools_list = df[[POP_COL, LAT_COL, LON_COL]].to_dict(orient="records")

    m.get_root().html.add_child(
        folium.Element(
            """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.js"></script>
    """
        )
    )
    m.get_root().script.add_child(folium.Element(CUSTOM_JS))

    m.get_root().render()
    header = m.get_root().header.render()
    body_html = m.get_root().html.render()
    script = m.get_root().script.render()

    return render_template(
        "index.html",
        header=header,
        body_html=body_html,
        script=script,
        top_5_schools=top_5_list,
        all_schools=all_schools_list,
    )


# --- TOP 5 필터링 API 엔드포인트 추가 ---
@app.route("/api/update_top5", methods=["POST"])
def update_top5():
    data = request.get_json()
    selected_categories = data.get("categories", [])

    # 선택된 카테고리에 해당하는 점수 컬럼 이름들을 가져옴
    score_cols_to_sum = [
        SCORE_COLUMN_MAP[cat] for cat in selected_categories if cat in SCORE_COLUMN_MAP
    ]

    df_copy = df.copy()  # 원본 DataFrame 수정을 방지하기 위해 복사본 사용

    # 선택된 컬럼이 있을 경우, 해당 컬럼들의 합으로 새로운 점수 계산
    if score_cols_to_sum:
        df_copy["dynamic_score"] = df_copy[score_cols_to_sum].sum(axis=1)
        # 동적 점수가 높은 순(내림차순)으로 정렬
        top_5_df = df_copy.sort_values(by="dynamic_score", ascending=False).head(5)
    else:
        # 아무것도 선택하지 않았을 경우, 기존 '점수 순위'로 정렬 (낮은 순)
        top_5_df = df_copy.sort_values(by=RANK_COL, ascending=True).head(5)

    top_5_list = top_5_df[[POP_COL, LAT_COL, LON_COL]].to_dict(orient="records")
    return jsonify(top_5_list)


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/script/<path:filename>")
def serve_script(filename):
    return send_from_directory("frontend/script", filename)


@app.route("/selected_facilities", methods=["POST"])
def selected_facilities():
    data = request.get_json()
    selected = data.get("selected", [])
    print("🔘 선택된 항목:", selected)
    return jsonify({"status": "ok", "received": selected})


@app.route("/route")
def route():
    from_lat = request.args.get("from_lat")
    from_lon = request.args.get("from_lon")
    to_lat = request.args.get("to_lat")
    to_lon = request.args.get("to_lon")

    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=full&geometries=geojson"
    print("📡 OSRM 요청:", osrm_url)
    try:
        r = requests.get(osrm_url, timeout=5)
        print("📨 응답 코드:", r.status_code)
        if r.status_code != 200:
            print("❌ 오류 응답:", r.text)
            return jsonify({"error": "Route not found"}), 500
        data = r.json()
        coords = data["routes"][0]["geometry"]["coordinates"]
        latlon_coords = [[c[1], c[0]] for c in coords]
        return jsonify({"route": latlon_coords})
    except Exception as e:
        print("❌ 예외 발생:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/nearby")
def nearby():
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
        is_facility_click = request.args.get("is_facility", "false").lower() == "true"

        selected_raw = request.args.get("selected")
        if selected_raw:
            selected_facilities = selected_raw.split(",")
        else:
            selected_facilities = []

        print(f"📋 요청받은 시설물: {selected_facilities}")

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude"}), 400

    response_data = {
        "restaurants": [],
        "conveniences": [],
        "cafes": [],
        "hospitals": [],
        "gncStations": [],
        "accommodations": [],
        "highways": [],
    }

    for facility_name in selected_facilities:
        if facility_name in CATEGORY_MAP:
            api_code = CATEGORY_MAP[facility_name]
            response_data[facility_name] = kakao_search(lat, lon, api_code)

    if not is_facility_click and "highways" in selected_facilities:
        unique_highways = {}
        clicked_point = (lat, lon)
        for _, row in df_highway.iterrows():
            highway_point = (row[H_LAT_COL], row[H_LON_COL])
            distance_km = geodesic(clicked_point, highway_point).km
            facility_name = row[H_NAME_COL]

            if (
                facility_name not in unique_highways
                or distance_km < unique_highways[facility_name]["distance_km"]
            ):
                unique_highways[facility_name] = {
                    "name": facility_name,
                    "lat": row[H_LAT_COL],
                    "lon": row[H_LON_COL],
                    "distance_km": distance_km,
                }
        sorted_highways = sorted(
            unique_highways.values(), key=lambda x: x["distance_km"]
        )
        response_data["highways"] = sorted_highways[:3]
    return jsonify(response_data)


if __name__ == "__main__":
    print("✅ http://127.0.0.1:5000 에서 확인하세요")
    app.run(debug=True)
