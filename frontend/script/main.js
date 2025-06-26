document.addEventListener('DOMContentLoaded', () => {

  const checkboxes = document.querySelectorAll('input[type="checkbox"][name="facility"]');

  const urlParams = new URLSearchParams(window.location.search);
  const isDarkMode = urlParams.get('dark_mode') === 'true';
  
  const lightIconUrls = {
      'hospitals': '/frontend/icons/hospital.png',
      'conveniences': '/frontend/icons/conveniences.png',
      'cafes': '/frontend/icons/cafes.png',
      'restaurants': '/frontend/icons/restaurant.png',
      'gncStations': '/frontend/icons/gas.png',
      'accommodations': '/frontend/icons/hotel.png',
      'highways': '/frontend/icons/highway.png'
  };

  const darkIconUrls = {
      'hospitals': '/frontend/icons/hospital.png',
      'conveniences': '/frontend/icons/conveniences.png',
      'cafes': '/frontend/icons/cafesw.png',
      'restaurants': '/frontend/icons/restaurant.png',
      'gncStations': '/frontend/icons/gasw.png',
      'accommodations': '/frontend/icons/hotelw.png',
      'highways': '/frontend/icons/highwayw.png'
  };

  function updateCheckboxIcons(isDark) {
      const panel = document.getElementById('info-box-1');
      if (!panel) return;

      const targetIcons = isDark ? darkIconUrls : lightIconUrls;

      Object.keys(lightIconUrls).forEach(value => {
          const input = panel.querySelector(`input[value="${value}"]`);
          if (input) {
              const label = input.closest('label');
              if (label) {
                  const img = label.querySelector('img');
                  if (img) {
                      img.src = targetIcons[value] || lightIconUrls[value];
                  }
              }
          }
      });
  }
  
  updateCheckboxIcons(isDarkMode);

  if (isDarkMode) {
    document.body.classList.add('dark-mode');
  }

  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      const checkedValues = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

      fetch('/selected_facilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected: checkedValues })
      })
        .then(res => res.json())
        .then(data => console.log("✅ 서버 응답:", data))
        .catch(err => console.error("❌ 서버 전송 실패:", err));
    });
  });
  updatePanelPositions();
});

function updatePanelPositions() {
    const panel1 = document.getElementById('panel-1');
    const panel2 = document.getElementById('panel-2');
    const panel4 = document.getElementById('panel-4');

    if (!panel1 || !panel2 || !panel4) {
        console.error('필요한 패널 요소 중 일부를 찾을 수 없습니다.');
        return;
    }
    const GAP = 25; // 패널 사이의 간격 (픽셀)
    const getPanelHeight = (panel) => panel.classList.contains('collapsed') ? 50 : panel.offsetHeight;

    // 첫 번째 패널의 실제 top 위치와 높이를 가져옵니다.
    const panel1Top = panel1.offsetTop;
    const panel1Height = getPanelHeight(panel1);

    // 두 번째 패널의 top 위치를 계산합니다.
    const panel2Top = panel1Top + panel1Height + GAP;
    panel2.style.top = `${panel2Top}px`;

    // 세 번째 패널의 top 위치를 계산합니다.
    const panel2Height = getPanelHeight(panel2);
    const panel4Top = panel2Top + panel2Height + GAP;
    panel4.style.top = `${panel4Top}px`;
}

function togglePanel(id) {
  const panel = document.getElementById(id);
  panel.classList.toggle('collapsed');
  updatePanelPositions();
}

function closePanel(id, event) {
  event.stopPropagation();
  const panel = document.getElementById(id);
  panel.classList.add('hidden');
}

/**
 * 오른쪽 학교 정보 패널을 보여주고, 등수 기반 통계를 계산하여 내용을 채우는 함수
 * @param {object} schoolData - Python에서 전달한 학교 정보 객체
 */
function showSchoolInfoPanel(schoolData) {
  const panel = document.getElementById('panel-3');
  if (!panel) return;

  // 1. ID로 학교 이름이 표시될 요소를 직접 선택합니다. (더 안정적인 방식)
  const titleElement = document.getElementById('school-title-text');
  
  // 2. 해당 요소가 존재하면 텍스트를 학교 이름으로 변경합니다.
  if (titleElement) {
    titleElement.textContent = schoolData.name || '이름 없음';
  }

  const panelContent = document.getElementById('info-box-3');

  panel.classList.remove('hidden');
  panel.classList.remove('collapsed');

  const createFacilityStat = (label, count, rank, totalCount) => {
    if (!rank || !totalCount || rank === 0) {
      return `<li style="margin-bottom: 8px;"><strong>${label}:</strong> ${count}개 (정보 없음)</li>`;
    }
    const percentile = (rank / totalCount) * 100;
    let topPercentile = 100 - percentile;
    let displayText;
    if (topPercentile <= 0) {
        displayText = "상위 0.1%";
    } else if (topPercentile >= 99.1) {
        displayText = "상위 100%";
    } else {
        displayText = `상위 ${topPercentile.toFixed(1)}%`;
    }
    return `<li style="margin-bottom: 8px;"><strong>${label}:</strong> ${count}개 (${displayText})</li>`;
  };

  const ranks = schoolData.ranks;
  const counts = schoolData.counts;
  const total_count = schoolData.total_count;

  // 패널 내용을 새로운 통계 정보로 채웁니다.
  panelContent.innerHTML = `
        <br>
        <h3 style="margin-top: 10px; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px;">
            기본 정보
        </h3>
        <ul style="list-style-type: none; padding-left: 5px; font-size: 16px;">
             <li style="margin-bottom: 8px;"><strong>주소:</strong> ${schoolData.address || '정보 없음'}</li>
             <li style="margin-bottom: 8px;"><strong>토지 규모:</strong> ${schoolData.land_size || '정보 없음'} m<sup>2</sup></li>
             <li style="margin-bottom: 8px;"><strong>건물 규모:</strong> ${schoolData.building_size || '정보 없음'} m<sup>2</sup></li>
             <li style="margin-bottom: 8px;"><strong>총 금액:</strong> ${schoolData.total_price || '정보 없음'} 천 원 (약 ${(schoolData.total_price/100000).toFixed(2)}억)</li>
             <li style="margin-bottom: 8px;"><strong>현재 상태:</strong> ${schoolData.current_status || '정보 없음'}</li>
        </ul>
        <br>
        <h3 style="margin-top: 10px; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px;">
            근방 3km 내 시설 수 (전라남도 내)
        </h3>
        <ul style="list-style-type: none; padding-left: 5px; font-size: 16px;">
            ${createFacilityStat('음식점', counts.restaurants, ranks.restaurants, total_count)}
            ${createFacilityStat('편의점', counts.conveniences, ranks.conveniences, total_count)}
            ${createFacilityStat('카페', counts.cafes, ranks.cafes, total_count)}
            ${createFacilityStat('병원', counts.hospitals, ranks.hospitals, total_count)}
            ${createFacilityStat('주유소', counts.gas_stations, ranks.gas_stations, total_count)}
            ${createFacilityStat('숙박시설', counts.accommodations, ranks.accommodations, total_count)}
        </ul>
        <br>
        <h3 style="margin-top: 10px; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px;">
          가장 가까운 IC/JC(TOP 3)
        </h3>
        <ul style="list-style-type: none; padding-left: 5px; font-size: 16px;">
          ${
            schoolData.nearest_highways && schoolData.nearest_highways.length > 0
              ? schoolData.nearest_highways.map(highway => 
                  `<li><strong>${highway.name}:</strong> ${highway.distance_km.toFixed(2)} km</li>`
                ).join('')
              : '<li>주변 고속도로 정보 없음</li>'
          }
        </ul>
    `;
}

window.addEventListener("DOMContentLoaded", () => {
  updatePanelPositions();
});

window.buildNearbyRequestUrl = function (lat, lon, isFacilityClick) {
  const selected = Array.from(document.querySelectorAll('input[name="facility"]:checked')).map(cb => cb.value).join(',');
  let fetchUrl = `/nearby?lat=${lat}&lon=${lon}&selected=${selected}`;
  if (isFacilityClick) fetchUrl += '&is_facility=true';
  return fetchUrl;
};

const modalContents = {
  settings: { title: '⚙️ 설정', content: `<label><input type="checkbox"> 다크 모드</label><br><h4>양쪽 패널 투명도 조절</h4><div class="slider-container"><label for="left-panel-opacity">왼쪽 패널:</label><input type="range" id="left-panel-opacity" min="0" max="10" value="9"><span id="left-opacity-value">0.9</span></div><div class="slider-container"><label for="right-panel-opacity">오른쪽 패널:</label><input type="range" id="right-panel-opacity" min="0" max="10" value="9"><span id="right-opacity-value">0.9</span></div><hr>` },
  source: { 
    title: '📖 출처 정보', 
    content: `
    <h3>데이터 출처</h3>
    <ul>
    <li>
      폐교 정보: 
      <a href="https://www.jne.go.kr/open/ad/as/view/abschSttusSig/selectAbschSttusSigList.do?mi=629" target="_blank">
      전라남도 교육청</a>
    </li>

    <li>
    폐교 정보: 
    <a href="https://www.eduinfo.go.kr/portal/theme/abolSchStatusPage.do?utm_source=chatgpt.com#none;" target="_blank">
    지방교육 재정 알리미</a>
    </li>

    <li>
    폐교 정보: 
    <a href="https://www.data.go.kr/tcs/dss/selectStdDataDetailView.do#tab-layer-recommend-data" target="_blank">
    data.co.kr</a>
    </li>

    <li>
    노인 인구 데이터: 
    <a href="https://www.data.go.kr/data/15069161/fileData.do#layer_data_infomation" target="_blank">
    data.co.kr</a>
    </li>

    <li>
    유동 인구 데이터: 
    <a href="https://bigdata-lifelog.kr/portal/mypage/mydata/data_use_state_new#nolink" target="_blank">
    라이프로그</a>
    </li>

    <li>
    고속도로 출입시설 데이터: 
    <a href="https://www.data.go.kr/data/15112762/fileData.do?recommendDataYn=Y" target="_blank">
    한국도로공사</a>
    </li>
    
    <li>
    병원 및 의료원 데이터: 
    <a href="https://www.data.go.kr/data/15069181/fileData.do#tab-layer-openapi" target="_blank">
    데이터포털</a>
    </li>

    <li>주거 인구 데이터: 
    <a href="https://kosis.kr/index/index.do" target="_blank">
    KOSIS</a>
    </li>

    <li>지도 API: 
    <a href="https://apis.map.kakao.com/web/" target="_blank">
    Kakao Maps API</a>
    </li>

    <li>경로 API: 
    <a href="https://www.openstreetmap.org/#map=16/37.40657/127.60906" target="_blank">
    OSRM API</a>
    </li>
    </ul>
    <hr style="margin: 15px 0;">

    <h3>이미지 출처</h3>
    <ul>
    <li>아이콘: Flaticon, Icons8</li></ul>
    <hr style="margin: 15px 0;">

    <h3>사용 프로그램</h3>
    <ul>
    <li>Visual Studio Code</li>
    <li>Jupyter Notebook</li>
    </ul>`},
  stack: { 
    title: '💻 기술 스택', 
    content: `
    <h3 style="margin-bottom: 10px;">프론트엔드 (Frontend)</h3>
    <ul style="margin: 0; padding-left: 20px;">
      <li><b>언어:</b> HTML, CSS, JavaScript</li>
      <li><b>지도 라이브러리:</b> Folium (Leaflet.js)</li>
      <li><b>아이콘:</b> Font Awesome</li>
    </ul>
    <hr style="margin: 15px 0;">

    <h3 style="margin-bottom: 10px;">백엔드 (Backend)</h3>
    <ul style="margin: 0; padding-left: 20px;">
      <li><b>언어:</b> Python</li>
      <li><b>웹 프레임워크:</b> Flask</li>
      <li><b>데이터 처리:</b> Pandas, Geopy</li>
    </ul>
    <hr style="margin: 15px 0;">

    <h3 style="margin-bottom: 10px;">사용 API 및 데이터</h3>
    <ul style="margin: 0; padding-left: 20px;">
      <li><b>외부 API:</b> Kakao Maps API (장소 검색), OSRM API (경로 탐색)</li>
      <li><b>데이터 형식:</b> CSV, JSON</li>
    </ul>
    <hr style="margin: 15px 0;">

    <h3 style="margin-bottom: 10px;">개발 환경 및 도구</h3>
    <ul style="margin: 0; padding-left: 20px;">
      <li>Visual Studio Code</li>
      <li>Jupyter Notebook</li>
    </ul>
    <br>
    
    <h3>개발자</h3>
    <p style="margin: 0;">장진서 박병주</p>` 
  }
};

const mainModalContainer = document.getElementById('main-modal-container');
const modalTitle = document.getElementById('modal-title');
const modalContent = document.getElementById('modal-content');
const closeModalBtn = document.getElementById('close-modal-btn');
const toolbar = document.querySelector('.floating-toolbar');

toolbar.addEventListener('click', (event) => {
  const trigger = event.target.closest('.modal-trigger');
  if (!trigger) return;

  const clickedTarget = trigger.dataset.modalTarget;
  const isModalVisible = !mainModalContainer.classList.contains('hidden');
  const currentOpenTarget = mainModalContainer.dataset.current;

  if (isModalVisible && clickedTarget === currentOpenTarget) {
    hideMainModal(); return;
  }

  const contentData = modalContents[clickedTarget];
  if (contentData) {
    modalTitle.textContent = contentData.title;
    modalContent.innerHTML = contentData.content;
    mainModalContainer.dataset.current = clickedTarget;
    mainModalContainer.classList.remove('hidden');
    if (clickedTarget === 'settings') initializeOpacityControls();
  }
});

function hideMainModal() {
  mainModalContainer.classList.add('hidden');
  delete mainModalContainer.dataset.current;
}
closeModalBtn.addEventListener('click', hideMainModal);

mainModalContainer.addEventListener('click', (event) => {
  // 클릭된 요소가 모달 배경 자체일 경우에만 닫기
  // (모달창 내부를 클릭했을 때는 닫히지 않음)
  if (event.target === mainModalContainer) {
    hideMainModal();
  }
});

function initializeOpacityControls() {
  const leftSlider = document.getElementById('left-panel-opacity');
  const rightSlider = document.getElementById('right-panel-opacity');
  const leftValueSpan = document.getElementById('left-opacity-value');
  const rightValueSpan = document.getElementById('right-opacity-value');
  const darkModeCheckbox = document.querySelector('#modal-content input[type="checkbox"]');
  const body = document.body;
  const leftPanels = document.querySelectorAll('.sidebar-box-left');
  const rightPanel = document.querySelector('.sidebar-box-right');

  if(leftSlider) leftSlider.addEventListener('input', e => { const val = e.target.value / 10; leftPanels.forEach(p => p.style.opacity = val); leftValueSpan.textContent = val.toFixed(1); });
  if(rightSlider) rightSlider.addEventListener('input', e => { const val = e.target.value / 10; if(rightPanel) rightPanel.style.opacity = val; rightValueSpan.textContent = val.toFixed(1); });

  if (darkModeCheckbox) {
    const urlParams = new URLSearchParams(window.location.search);
    const isDarkMode = urlParams.get('dark_mode') === 'true';
    darkModeCheckbox.checked = isDarkMode;
    body.classList.toggle('dark-mode', isDarkMode);
    darkModeCheckbox.addEventListener('change', function () {
      urlParams.set('dark_mode', this.checked ? 'true' : 'false');
      if (!this.checked) urlParams.delete('dark_mode');
      window.location.search = urlParams.toString();
    });
  }
  if (leftSlider) leftPanels.forEach(panel => { panel.style.opacity = leftSlider.value / 10; });
  if (rightSlider && rightPanel) rightPanel.style.opacity = rightSlider.value / 10;
}

// --- TOP 5 필터 기능 및 패널 업데이트 로직 ---

/**
 * TOP 5 패널 목록을 채우는 함수
 * @param {Array} schools - 학교 정보 배열
 */
function populateTop5Panel(schools) {
  const infoBox = document.getElementById('info-box-2');
  if (!infoBox) return;

  infoBox.innerHTML = ''; // 기존 내용 초기화
  const list = document.createElement('ol');

  schools.forEach(school => {
    const listItem = document.createElement('li');
    const nameSpan = document.createElement('span');
    nameSpan.textContent = school.폐교명;
    const moveButton = document.createElement('button');
    moveButton.textContent = '이동';
    moveButton.onclick = () => moveToSchool(school.위도, school.경도);
    listItem.appendChild(nameSpan);
    listItem.appendChild(moveButton);
    list.appendChild(listItem);
  });
  infoBox.appendChild(list);
}

/**
 * 지정된 위도, 경도로 지도를 이동하고 마커를 클릭하는 함수
 * @param {number} lat - 위도
 * @param {number} lon - 경도
 */
function moveToSchool(lat, lon) {
  if (!window._mainMap) {
    console.error("지도 객체를 찾을 수 없습니다.");
    return;
  }
  window._mainMap.setView([lat, lon], 13);
  window._mainMap.eachLayer(layer => {
    if (layer instanceof L.MarkerClusterGroup) {
      layer.eachLayer(marker => {
        const markerLatLng = marker.getLatLng();
        if (markerLatLng.lat === lat && markerLatLng.lng === lon) {
          layer.zoomToShowLayer(marker, () => marker.fire('click'));
        }
      });
    }
  });
}

/**
 * 필터 모달창의 확인 버튼을 눌렀을 때 실행되는 함수
 */
function applyTop5Filter() {
    const checkboxes = document.querySelectorAll('#filter-checkboxes input[type="checkbox"]:checked');
    const selectedCategories = Array.from(checkboxes).map(cb => cb.value);

    fetch('/api/update_top5', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ categories: selectedCategories })
    })
    .then(res => res.json())
    .then(newTop5List => {
        populateTop5Panel(newTop5List); // 받아온 새 목록으로 패널 업데이트
        document.getElementById('filter-modal').classList.add('hidden'); // 모달 닫기
    })
    .catch(error => console.error('Error updating TOP 5 list:', error));
}



// 페이지 로드 시 실행될 초기화 함수들
document.addEventListener('DOMContentLoaded', () => {
  const searchContainer = document.getElementById('search-container');
  const searchInput = document.getElementById('search-input');
  const searchIcon = document.getElementById('search-icon');
  const suggestionsList = document.getElementById('search-suggestions');

  if (searchContainer && searchInput && searchIcon && suggestionsList) {
    searchContainer.addEventListener('click', (event) => {
      event.stopPropagation();
      });
    searchIcon.addEventListener('click', () => {
      if (!searchContainer.classList.contains('active')) {
        searchContainer.classList.add('active');
        searchInput.focus();
        }
      });

    document.addEventListener('click', () => {
      if (searchContainer.classList.contains('active')) {
        searchContainer.classList.remove('active');
        suggestionsList.classList.add('hidden');
        searchInput.value = '';
        }
      });
      searchInput.addEventListener('input', () => {
        if (typeof allSchoolsData === 'undefined') return;
        const query = searchInput.value.trim().toLowerCase();
        suggestionsList.innerHTML = ''; // 목록 초기화
        suggestionsList.classList.add('hidden');

        if (query.length > 0) {
          const filteredSchools = allSchoolsData.filter(school =>
            school.폐교명.toLowerCase().includes(query)
            );

          if (filteredSchools.length > 0) {
            filteredSchools.slice(0, 10).forEach(school => {
              const li = document.createElement('li');
              li.textContent = school.폐교명;
              li.dataset.lat = school.위도;
              li.dataset.lon = school.경도;
              suggestionsList.appendChild(li);
              });
          suggestionsList.classList.remove('hidden');
          }
        }
      });

      suggestionsList.addEventListener('click', (e) => {
        if (e.target.tagName === 'LI') {
          const lat = parseFloat(e.target.dataset.lat);
          const lon = parseFloat(e.target.dataset.lon);

          if (lat && lon) {
            moveToSchool(lat, lon);
          }
          searchInput.value = '';
          suggestionsList.classList.add('hidden');
          searchContainer.classList.remove('active');
        }
      });
    }


  // 초기 TOP 5 목록 채우기 (index.html에 정의된 topSchoolsData 변수 사용)
  if (typeof topSchoolsData !== 'undefined') {
    populateTop5Panel(topSchoolsData);
  }

  // 필터 모달 관련 요소 가져오기
  const filterModal = document.getElementById('filter-modal');
  const openFilterBtn = document.getElementById('filter-top5-btn');
  const closeFilterBtn = document.getElementById('close-filter-modal-btn');
  const applyFilterBtn = document.getElementById('apply-filter-btn');
  const filterCheckboxesContainer = document.getElementById('filter-checkboxes');
  
  // 필터링할 항목 정의
  const filterOptions = {
      'hospitals': '병원',
      'conveniences': '편의점',
      'cafes': '카페',
      'restaurants': '음식점',
      'gncStations': '주유소 & 충전소',
      'accommodations': '숙박시설'
  };

  // 필터 모달에 체크박스 동적 생성
  for (const [value, text] of Object.entries(filterOptions)) {
      const label = document.createElement('label');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.value = value;
      checkbox.checked = true; // 기본적으로 모두 체크된 상태
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(` ${text}`));
      filterCheckboxesContainer.appendChild(label);
  }

  // 이벤트 리스너 할당
  openFilterBtn.addEventListener('click', () => filterModal.classList.remove('hidden'));
  closeFilterBtn.addEventListener('click', () => filterModal.classList.add('hidden'));
  filterModal.addEventListener('click', (event) => {
    // 클릭된 요소가 모달 배경(#filter-modal) 자체일 경우에만 닫기
    if (event.target === filterModal) {
        filterModal.classList.add('hidden');
    }
  });
  applyFilterBtn.addEventListener('click', applyTop5Filter);
});