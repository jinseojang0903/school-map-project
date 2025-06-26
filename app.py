import pandas as pd
import folium
import requests
from folium.plugins import MarkerCluster
from flask import Flask, render_template, request, jsonify
from geopy.distance import geodesic
import os
from flask import send_from_directory
import json

app = Flask(__name__, template_folder="frontend", static_folder="frontend")

# --- 상수 정의 ---
CSV_PATH = "./데이터/주소위도경도.csv"
HIGHWAY_CSV_PATH = "./데이터/고속도로출입시설.csv"

# 파일 존재 여부 확인
if not os.path.exists(CSV_PATH):
    print(f"오류: '{CSV_PATH}' 파일을 찾을 수 없습니다. 스크립트와 같은 디렉토리에 '데이터' 폴더를 만들고 CSV 파일을 넣어주세요.")
    exit()
if not os.path.exists(HIGHWAY_CSV_PATH):
    print(f"오류: '{HIGHWAY_CSV_PATH}' 파일을 찾을 수 없습니다.")
    exit()

# CSV 컬럼명
LAT_COL, LON_COL, POP_COL = "위도", "경도", "폐교명"
H_NAME_COL, H_LAT_COL, H_LON_COL = "IC/JC명", "위도", "경도"

# 카카오 API 설정
REST_API_KEY = os.environ.get('KAKAO_API_KEY', "c6167fc9bb70ca9ea487094d849bb1f5")
SEARCH_RADIUS = 3000  # 검색 반경 (미터)

# 카테고리 코드 매핑
CATEGORY_MAP = {
    "restaurants": "FD6",
    "conveniences": "CS2",
    "cafes": "CE7",
    "hospitals": "HP8",
    "gncStations": "OL7",
    "accommodations": "AD5",
}

# --- 데이터 로드 ---
def load_csv_data(path, lat_col, lon_col):
    """CSV 파일을 로드하고 위도/경도 컬럼을 정리하는 함수"""
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949")
    df = df.dropna(subset=[lat_col, lon_col]).astype({lat_col: float, lon_col: float})
    return df

df = load_csv_data(CSV_PATH, LAT_COL, LON_COL)
df_highway = load_csv_data(HIGHWAY_CSV_PATH, H_LAT_COL, H_LON_COL)

total_school_count = len(df)

CUSTOM_JS ='''
cnt = 0;
const MIN_ZOOM_LEVEL =8;

window.onload = function () {
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
        const color_arr = ['red', 'blue', 'green'];

        window._mainMap.on('zoomend', function() {
            const currentZoom = window._mainMap.getZoom();
            if (currentZoom < MIN_ZOOM_LEVEL) {
                window._mainMap.setZoom(MIN_ZOOM_LEVEL);
            }
        });

        // (createCustomIcon, addMarker, drawRoute, resetAllRoads 함수는 기존과 동일)
        function createCustomIcon(category) {
            const iconUrls = { 
            cafes: "/frontend/icons/cafes.png", 
            conveniences: "/frontend/icons/conveniences.png", 
            restaurants: "/frontend/icons/restaurant.png", 
            hospitals: "/frontend/icons/hospital.png", 
            accommodations:"/frontend/icons/hotel.png", 
            gncStations: "/frontend/icons/gas.png", 
            highway: "/frontend/icons/highway.png", 
            default: "/frontend/icons/highway.png" };

            return L.icon({ iconUrl: iconUrls[category] || iconUrls.default, iconSize: [32, 32], iconAnchor: [16, 32], popupAnchor: [0, -32] });
        }
        function addMarker(lat, lon, name, category, isFacility, address = null, phone = null) {
            let popupText = `<b>${name}</b>`;
            if (address) popupText += `<br>📍 ${address}`;
            if (phone) popupText += `<br>📞 ${phone}`;
            const marker = L.marker([lat, lon], { icon: createCustomIcon(category), isFacilityMarker: true });
            marker.bindPopup(popupText).addTo(facilityLayerGroup);
        }
        function drawRoute(fromLat, fromLon, toLat, toLon) {
            const url = `/route?from_lat=${fromLat}&from_lon=${fromLon}&to_lat=${toLat}&to_lon=${toLon}`;
            fetch(url).then(res => res.json()).then(result => { if (result.route) { cnt += 1; const polyline = L.polyline(result.route, { color: color_arr[cnt-1], weight: 10, opacity: 0.5 }); polyline.addTo(routeLayerGroup); } }).catch(err => console.error("❌ 경로 요청 실패:", err));
        }
        function resetAllRoads() { routeLayerGroup.clearLayers(); cnt = 0; }


        // ▼▼▼▼▼ 여기가 핵심 수정 부분입니다 ▼▼▼▼▼
        window._mainMap.on('popupopen', function(e){
            const clickedLayer = e.popup._source;
            const isFacilityClick = clickedLayer.options.isFacilityMarker || false;
            
            // 폐교 마커가 클릭되었을 때만 실행
            if (!isFacilityClick) {
                console.log("✅ 폐교 마커 팝업 열림 이벤트 발생");

                // 팝업 요소에서 직접 .school-data 클래스를 찾습니다. (더 안정적인 방법)
                const popupElement = e.popup.getElement();
                const schoolDataElement = popupElement.querySelector('.school-data');
                
                console.log("🔍 데이터 요소 찾는 중...", schoolDataElement);

                if (schoolDataElement) {
                    console.log("👍 데이터 요소 찾음! 내용:", schoolDataElement.textContent);
                    try {
                        const schoolData = JSON.parse(schoolDataElement.textContent);
                        console.log("📦 데이터 파싱 성공:", schoolData);
                        
                        // 부모 창의 함수를 호출하여 오른쪽 패널을 엽니다.
                        window.parent.showSchoolInfoPanel(schoolData);

                        // 팝업은 즉시 닫아서 사용자에게 보이지 않게 합니다.
                        window._mainMap.closePopup(e.popup);
                        console.log("🎉 패널 열기 함수 호출 및 팝업 닫기 완료!");

                    } catch (error) {
                        console.error("❌ 데이터 파싱 중 오류 발생:", error);
                    }
                } else {
                    console.error("❗️'.school-data' 요소를 팝업에서 찾지 못했습니다.");
                }
                
                // 주변 시설물 마커 초기화
                facilityLayerGroup.clearLayers();
                resetAllRoads();
            }

            // 주변 시설물 검색 로직은 기존과 동일
            const {lat, lng} = e.popup._latlng;
            const selectedFacilities = Array.from(window.parent.document.querySelectorAll('input[name="facility"]:checked')).map(cb => cb.value).join(',');
            let fetchUrl = `/nearby?lat=${lat}&lon=${lng}&selected=${selectedFacilities}`;
            if (isFacilityClick) { fetchUrl += '&is_facility=true'; }
            
            fetch(fetchUrl)
                .then(response => response.json())
                .then(data => {
                    data.restaurants.forEach(o => addMarker(o.lat, o.lon, o.name, 'restaurants', true, o.address, o.phone));
                    data.hospitals.forEach(o => addMarker(o.lat, o.lon, o.name, 'hospitals', true, o.address, o.phone));
                    data.conveniences.forEach(o => addMarker(o.lat, o.lon, o.name, 'conveniences', true, o.address, o.phone));
                    data.cafes.forEach(o => addMarker(o.lat, o.lon, o.name, 'cafes', true, o.address, o.phone));
                    data.gncStations.forEach(o => addMarker(o.lat, o.lon, o.name, 'gncStations', true, o.address, o.phone));
                    data.accommodations.forEach(o => addMarker(o.lat, o.lon, o.name, 'accommodations', true, o.address, o.phone));
                    if (data.highways && data.highways.length > 0) {
                        data.highways.forEach(o => { const popupText = `${o.name}<br><b>거리: ${o.distance_km.toFixed(2)} km</b>`; addMarker(o.lat, o.lon, popupText, 'black'); drawRoute(lat, lng, o.lat, o.lon); });
                    }
                })
                .catch(error => { console.error('Fetch Error:', error); });
        });
    } else {
        console.error("🛑 지도 객체(map object)를 찾을 수 없습니다.");
    }
};
'''

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
            "x": lon, "y": lat,
            "radius": SEARCH_RADIUS,
            "size": 15, "page": page,
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
                    all_results.append({
                        "name": d["place_name"],
                        "lat": float(d["y"]),
                        "lon": float(d["x"]),
                        "address": d.get("road_address_name", "주소 없음"),
                        "phone": d.get("phone", "번호 없음")
                    })
            if data.get("meta", {}).get("is_end", True):
                break
        except Exception as e:
            print(f"Kakao request 요청 실패 (page: {page}):", e)
            break
    return all_results

@app.route("/")
def index():
    #다크모드
    is_dark_mode = request.args.get('dark_mode') == 'true'

    center = [34.5, 127]

    map_tiles = 'cartodbdarkmatter' if is_dark_mode else 'CartoDB positron'
    m = folium.Map(location=center, zoom_start=9, tiles=map_tiles, zoom_control=False)
    
    m.get_name = lambda: "map"
    cluster = MarkerCluster().add_to(m)

    for _, r in df.iterrows():
        # JavaScript로 전달할 학교 정보를 딕셔너리 형태로 만듭니다.
        school_info = {
            "name": r.get("폐교명"),
            "address": r.get("소재지도로명주소", "정보 없음"),
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
                "accommodations": r.get("숙박시설 수", 0)
            },
            "total_count": total_school_count
        }
        school_info_json = json.dumps(school_info, ensure_ascii=False)

        # 팝업 HTML 생성 부분은 이전과 동일합니다.
        popup_html = f"""
            <div class="school-data" style="display: none;">{school_info_json}</div>
            <b>{school_info['name']}</b><br>
            <small>정보를 보려면 클릭하세요</small>
        """
        popup = folium.Popup(popup_html, max_width=300)
        folium.Marker(
            [r[LAT_COL], r[LON_COL]],
            popup=popup,
        ).add_to(cluster)


    m.get_root().html.add_child(folium.Element("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.js"></script>
    """))
    m.get_root().script.add_child(folium.Element(CUSTOM_JS))

    # ▼▼▼▼▼ 2. 지도 부품 분해 (핵심 변경사항) ▼▼▼▼▼
    m.get_root().render()
    header = m.get_root().header.render()
    body_html = m.get_root().html.render()
    script = m.get_root().script.render()

    # ▼▼▼▼▼ 3. 부품들을 템플릿에 전달 ▼▼▼▼▼
    return render_template(
        "index.html",
        header=header,
        body_html=body_html,
        script=script
    )


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
        is_facility_click = request.args.get('is_facility', 'false').lower() == 'true'
        
        # 쿼리 파라미터 파싱 로직
        selected_raw = request.args.get('selected')
        if selected_raw:  # 파라미터가 존재하고, 내용이 있는 경우
            selected_facilities = selected_raw.split(',')
        else:  # 파라미터가 없거나, 내용이 없는 경우 (e.g. selected=)
            selected_facilities = []
            
        print(f"📋 요청받은 시설물: {selected_facilities}")

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude"}), 400

    # 응답 데이터 초기화
    response_data = {
        "restaurants": [], "conveniences": [], "cafes": [],
        "hospitals": [], "gncStations": [], "accommodations": [], "highways": []
    }

    # 선택된 시설에 대해서만 검색 수행
    for facility_name in selected_facilities:
        if facility_name in CATEGORY_MAP:
            api_code = CATEGORY_MAP[facility_name]
            response_data[facility_name] = kakao_search(lat, lon, api_code)
    
    # 'highways'가 선택되었을 때만 고속도로 정보 검색
    if not is_facility_click and 'highways' in selected_facilities:
        unique_highways = {}
        clicked_point = (lat, lon)
        for _, row in df_highway.iterrows():
            highway_point = (row[H_LAT_COL], row[H_LON_COL])
            distance_km = geodesic(clicked_point, highway_point).km
            facility_name = row[H_NAME_COL]
            
            if facility_name not in unique_highways or distance_km < unique_highways[facility_name]['distance_km']:
                unique_highways[facility_name] = {
                    "name": facility_name,
                    "lat": row[H_LAT_COL],
                    "lon": row[H_LON_COL],
                    "distance_km": distance_km
                }
        sorted_highways = sorted(unique_highways.values(), key=lambda x: x["distance_km"])
        response_data["highways"] = sorted_highways[:3]
    return jsonify(response_data)

if __name__ == "__main__":
    print("✅ http://127.0.0.1:5000 에서 확인하세요")
    app.run(debug=True)