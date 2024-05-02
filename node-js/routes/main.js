
const express = require('express');
const router = express.Router();
const axios = require('axios');
const mysql = require('mysql2/promise');
const haversine = require('haversine');

require('dotenv').config({ path: "../.env" });

// Kakao REST API 키
const KAKAO_API_KEY = process.env.KAKAO_API_KEY;


// 데이터베이스 연결 설정
const pool = mysql.createPool({
  host: process.env.host,
  user: process.env.user,
  port: process.env.port,
  password: process.env.password,
  database: process.env.database
});

router.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});



// 위치 정보 가져오기
async function getLocation(address) {
  const url = 'https://dapi.kakao.com/v2/local/search/keyword.json';
  const headers = {
    Authorization: `KakaoAK ${KAKAO_API_KEY}`
  };
  const response = await axios.get(url, { headers, params: { query: address } });
  const documents = response.data.documents[0];
  return { latitude: parseFloat(documents.y), longitude: parseFloat(documents.x) };
}

// 가장 가까운 랜드마크 찾기
async function findClosestLandmark(latitude, longitude) {
  const [rows] = await pool.query('SELECT 랜드마크, 위도, 경도 FROM landmark');
  let minDistance = Infinity;
  let closestLandmark = null;

  rows.forEach(row => {
    const start = { latitude, longitude };
    const end = { latitude: row.위도, longitude: row.경도 };
    const distance = haversine(start, end, { unit: 'km' });

    if (distance < minDistance) {
      minDistance = distance;
      closestLandmark = row.랜드마크;
    }
  });

  return closestLandmark;
}


// mysql db connection test
router.get('/test-db-connection', async (req, res) => {
  try {
    const connection = await pool.getConnection(); // 연결 시도
    res.send('Database connection successful!');   // 연결 성공 메시지
    connection.release();                          // 연결 해제
  } catch (error) {
    console.error('Database connection failed:', error);
    res.status(500).send('Database connection failed'); // 연결 실패 메시지
  }
});

// congestion 테이블 데이터 조회 API
router.get('/get-congestion', async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT * FROM congestion');

    // 각 행의 날짜/시간 데이터를 UTC로 변환
    const modifiedRows = rows.map(row => {
      if (row.inquiry_time) {
        // MySQL에서는 시간이 UTC로 저장되어 있을 수 있으므로, 클라이언트에게는 이를 ISO 문자열로 반환
        row.inquiry_time = new Date(row.inquiry_time + 'Z').toISOString();
      }
      return row;
    });

    res.json(modifiedRows);
  } catch (error) {
    console.error('Error during database query:', error);
    res.status(500).send('Error while fetching data from database');
  }
});

// congestion 데이터 조회 및 외부 API 호출
router.get('/search-congestion', async (req, res) => {
  const { location, input_time } = req.query;
  let closestLandmark; // closestLandmark 변수를 미리 선언

  // 가장 가까운 랜드마크 찾기
  try {
    const { latitude, longitude } = await getLocation(location);
    closestLandmark = await findClosestLandmark(latitude, longitude);

  } catch (error) {
    console.error('Error during API call:', error);
    res.status(500).send('Error fetching congestion data');
  }

  try {
    const [rows] = await pool.query(
      'SELECT * FROM congestion WHERE area_nm = ? AND inquiry_time = ?',
      [closestLandmark, input_time]
    );

    console.log(input_time);

    if (rows.length > 0) {
      res.render('congestion_inquiry.ejs', { code: 200, message: "혼잡도 데이터 조회에 성공하였습니다.", data: rows[0] });
    } else {
      // 데이터가 없을 경우 외부 API 호출
      const apiResponse = await axios.get('http://localhost:3000/location/congestion-test', {
        params: { location, input_time: input_time }
      });

      // API에서 받은 데이터 처리
      const result_data = apiResponse.data.data; // 가정: API 응답에 data 필드가 있고 그 안에 필요한 데이터가 있다.
      // const { area_nm: closestLandmark, inquiry_time: newInquiryTime } = result_data;


      // 다시 데이터 조회
      const [newRows] = await pool.query(
        'SELECT * FROM congestion WHERE area_nm = ? AND inquiry_time = ?',
        [closestLandmark, input_time]
      );

      // 응답 데이터 전송
      if (newRows.length > 0) {
        // res.render('congestion_inquiry.ejs', { code: 200, message: "혼잡도 데이터 조회에 성공하였습니다.", data: newRows });
        res.render('congestion_inquiry.ejs', { code: 200, message: "혼잡도 데이터 조회에 성공하였습니다.", data: newRows[0] });

      } else {
        res.render('congestion_inquiry.ejs', { code: 404, message: "데이터가 없습니다.", data: {} });
      }
    }
  } catch (error) {
    console.error('Error during database query or API call', error);
    res.status(500).send('Internal Server Error');
  }
});

// 근처 혼잡도 조회
router.get('/search-hotspot', async (req, res) => {
  const { place, congestion, input_time } = req.query;
  console.log(input_time)
  try {
    // 서버에 HTTP GET 요청 보내기
    const date = new Date(input_time);
    // Korea is generally +9 hours from UTC
    const koreaTime = new Date(date.getTime() + (9 * 60 * 60 * 1000));
    // Format the date to 'YYYY-MM-DD HH:MM' format
    const formattedTime = koreaTime.toISOString().replace('T', ' ').substring(0, 16);

    console.log(formattedTime);  // Output the formatted Korean time

    // Server HTTP GET request with the Korean time
    const response = await axios.get('http://localhost:3000/location/search/hot', {
      params: { place, congestion, input_time: formattedTime }
    });
    // 응답 받은 데이터를 클라이언트에게 반환
    // res.json(response.data);
    console.log(response.data.data.inquiry_time)
    res.render('congestion_inquiry.ejs', response.data);

  } catch (error) {
    console.error('Error during database query or API call', error);
    res.status(500).send('Internal Server Error');
  }
});

// 이벤트 조회
router.get('/search-event', async (req, res) => {
  const { area_nm } = req.query;
  try {
    // event 테이블에서 해당 area_nm이 있는지 조회
    const [rows] = await pool.query(
      'SELECT * FROM event WHERE area_nm = ?',
      [area_nm]
    );

    if (rows.length > 0) {
      // 해당 area_nm이 있는 경우 데이터 반환
      res.render('event.ejs', { code: 200, message: "이벤트 데이터 조회에 성공하였습니다.", data: rows });
      // res.json({ code: 200, message: "이벤트 데이터 조회에 성공하였습니다.", data: rows });

    } else {
      // 해당 area_nm이 없는 경우 외부 API 호출
      const externalResponse = await axios.get('http://localhost:3000/location/search/event', {
        params: { area_nm }
      });

      // 외부 API 호출 후 응답 확인
      if (externalResponse.data.code === 404) {
        // 이벤트 데이터가 없는 경우
        res.render('event.ejs', { code: 404, message: '이벤트 데이터가 없습니다.', data: [] });
      } else {
        // 다시 event 테이블 조회
        const [newRows] = await pool.query(
          'SELECT * FROM event WHERE area_nm = ?',
          [area_nm]
        );

        // 조회된 데이터 반환
        res.render('event.ejs', { code: 200, message: "이벤트 데이터 조회에 성공하였습니다.", data: rows });
      }
    }
  } catch (error) {
    console.error('Error during database query or API call', error);
    res.status(500).send('Internal Server Error');
  }
});

// 추천 페이지 구현
router.get('/recommendation', async (req, res) => {
  const { area_nm, input_time } = req.query;

  // console.log(input_time)

  try {
    if (!area_nm) {
      return res.status(400).render('error.ejs', { message: "Area name is required." });
    }
    // const date = new Date(input_time);
    // // Korea is generally +9 hours from UTC
    // const koreaTime = new Date(date.getTime() + (9 * 60 * 60 * 1000));
    // // Format the date to 'YYYY-MM-DD HH:MM' format
    // const formattedTime = koreaTime.toISOString().replace('T', ' ').substring(0, 16);
    // console.log(formattedTime)

    // input_time으로부터 분기 계산하기
    const date = new Date(input_time);
    const month = date.getMonth() + 1; // getMonth()는 0부터 시작하므로 1을 더함
    let quarter;

    if (month >= 1 && month <= 3) {
      quarter = 1;
    } else if (month >= 4 && month <= 6) {
      quarter = 2;
    } else if (month >= 7 && month <= 9) {
      quarter = 3;
    } else if (month >= 10 && month <= 12) {
      quarter = 4;
    }

    // Render event.ejs with data
    res.render('recommend.ejs', {
      code: 200,
      message: "추천 페이지로 이동했습니다.",
      data: {
        "area_nm": area_nm,
        "quarter": quarter
      }
    });
  } catch (error) {
    console.error('Error fetching data:', error);
    res.status(500).render('error.ejs', { message: "Internal Server Error" });
  }
});

router.post('/recommend-store', async (req, res) => {
  const { location, category, gender, age, quarter } = req.body
  const genderKorean = gender === 'female' ? '여성' : '남성';
  const apiResponse = await axios.post('http://0.0.0.0:3000/location/recommend/store',
    { location, category, gender: genderKorean, age, quarter });
  // console.log(apiResponse.data.data.여성_sales)
  res.json(apiResponse.data);

});

// 업종 추천
router.post('/recommend-category', async (req, res) => {
  const { location, gender, age, quarter } = req.body;
  const genderKorean = gender === 'female' ? '여성' : '남성';

  try {
    // 먼저 성별 데이터의 존재 여부를 확인
    var [genderResults] = await pool.query(`
          SELECT location, service_code, gender_or_age, quarter, sales FROM category
          WHERE location = ?
          AND gender_or_age = ?
          AND quarter = ?
      `, [location, gender, quarter]);

    // 연령 데이터의 존재 여부를 확인
    var [ageResults] = await pool.query(`
          SELECT location, service_code, gender_or_age, quarter, sales FROM category
          WHERE location = ?
          AND gender_or_age = ?
          AND quarter = ?
      `, [location, `age_${age}`, quarter]);

    // 성별 및 연령 데이터 모두 없을 경우 FastAPI 호출
    if (genderResults.length === 0 || ageResults.length === 0) {
      const apiResponse = await axios.post('http://0.0.0.0:3000/location/recommend/category', { location, gender: genderKorean, age, quarter });
      if (apiResponse.data.code === 200) {
        // 성별데이터가 없다면 성별 데이터 저장
        if (genderResults.length == 0) {
          const genderData = apiResponse.data.data.gender;
          await saveData(gender, quarter, location, genderData);

          // 저장 후 다시 쿼리 날리기
          [genderResults] = await pool.query(`
                SELECT location, service_code, gender_or_age, quarter, sales FROM category
                WHERE location = ?
                AND gender_or_age = ?
                AND quarter = ?
              `, [location, gender, quarter]);
        }

        // 연령 데이터가 없다면 연령 데이터 저장
        if (ageResults.length === 0) {
          const ageData = apiResponse.data.data.age;
          await saveData(`age_${age}`, quarter, location, ageData);


          // 연령 데이터의 존재 여부를 확인
          [ageResults] = await pool.query(`
                  SELECT location, service_code, gender_or_age, quarter, sales FROM category
                  WHERE location = ?
                  AND gender_or_age = ?
                  AND quarter = ?
                `, [location, `age_${age}`, quarter]);
        }

        res.json({ code: 200, message: "데이터를 불러왔습니다.", data: { genderResults, ageResults } });
      } else {
        throw new Error("API 호출 실패 혹은 데이터 부재");
      }
    } else {
      res.json({ code: 200, message: "데이터가 이미 존재합니다.", data: { genderResults, ageResults } });
    }
  } catch (error) {
    console.error('데이터베이스 쿼리 또는 외부 API 호출 중 오류 발생:', error);
    res.status(500).send('내부 서버 오류');
  }
});

async function saveData(genderOrAge, quarter, location, data) {
  await Promise.all(Object.entries(data).map(async ([serviceCode, sales]) => {
    await pool.execute(`
          INSERT INTO category (location, service_code, quarter, gender_or_age, sales)
          VALUES (?, ?, ?, ?, ?)
          ON DUPLICATE KEY UPDATE sales = VALUES(sales)
      `, [location, serviceCode, quarter, genderOrAge, sales]);
  }));
}



async function handleMissingCodes(codes, location, category, gender, age, quarter) {
  var savedData = [];
  // 외부 API 호출 및 데이터베이스에 저장
  await Promise.all(codes.map(async code => {
    const apiResponse = await axios.post('http://0.0.0.0:3000/location/recommend/store', {
      location,
      category,
      gender,
      age,
      quarter
    });

    if (apiResponse.data.code === 200) {
      // 데이터베이스에 각 상권 데이터 저장
      const genderKey = `${gender}_sales`;
      await Promise.all(apiResponse.data.data[genderKey].map(async (item) => {
        console.log(item)
        const insertResult1 = await pool.execute(`
              INSERT INTO location (district_code, service_code, quarter, gu_code, dong_code, ${mysql.escapeId(gender)})
              VALUES (?, ?, ?, ?, ?, ?)
          `, [
          item.상권_코드_명,
          category,
          quarter,
          item.자치구_코드_명,
          item.행정동_코드_명,
          item.sales
        ]);

        // savedData.push(insertResult1);
      }));

      // 나이에 따른 데이터를 가정하고 추가 저장 로직을 구현
      const ageKey = `age_${age}_sales`;

      await Promise.all(apiResponse.data.data[ageKey].map(async (item) => {
        const insertResult2 = await pool.execute(`
              INSERT INTO location (district_code, service_code, quarter, gu_code, dong_code, ${mysql.escapeId('age_' + age)})
              VALUES (?, ?, ?, ?, ?, ?)
          `, [
          item.상권_코드_명,
          category,
          quarter,
          item.자치구_코드_명,
          item.행정동_코드_명,
          item.sales
        ]);

        // savedData.push(insertResult2);
      }));

    } else {
      throw new Error("API 호출 실패 혹은 데이터 부재");
    }
    savedData.push(apiResponse.data); // 예시로 응답 데이터를 그대로 저장
  }));
  return savedData;
}
// router.post('/recommend-store', async (req, res) => {
//   const { location, category, gender, age, quarter } = req.body;
//   const genderKorean = gender === 'female' ? '여성' : '남성';

//   try {
//     const { latitude, longitude } = await getLocation(location);

//     // 가장 가까운 위치 데이터 조회
//     const nearestQuery = `
//         SELECT 상권_코드_명 FROM store
//         ORDER BY (POW((위도 - ?), 2) + POW((경도 - ?), 2))
//         LIMIT 10;
//     `;

//     const [nearest] = await pool.query(nearestQuery, [latitude, longitude]);
//     const districtCodes = nearest.map(entry => entry.상권_코드_명);

//     const locationQuery = `
//         SELECT * FROM location
//         WHERE district_code IN (?);
//     `;

//     const [locations] = await pool.query(locationQuery, [districtCodes]);
//     console.log("locationQuery:", locations);
//     if (location.length == 0) {
//       const savedData = await handleMissingCodes(districtCodes, location, category, genderKorean, age, quarter);
//       res.json({
//         code: 202,
//         message: "일부 데이터가 외부 API에서 가져와졌으며 데이터베이스에 저장되었습니다.",
//         data: savedData
//       });
//     }
//     // if문에 안걸리면 nearest에 데이터가 있는 것임
//     // 존재하지 않거나 데이터가 누락된 district_code 확인
//     const existingDistrictCodes = nearest.map(entry => entry.district_code);
//     const missingDistrictCodes = existingDistrictCodes.filter(code => !existingDistrictCodes.includes(code));

//     // 기존 위치에서 누락된 데이터 확인
//     const nullDataCodes = nearest.filter(entry => entry[gender] === null || entry['age_' + age] === null).map(entry => entry.district_code);

//     // 누락된 코드의 합집합 찾기
//     const allMissingCodes = [...new Set([...missingDistrictCodes, ...nullDataCodes])];

//     if (allMissingCodes.length > 0) {
//       // 외부 API 호출 및 데이터베이스 저장 로직
//       const savedData = await handleMissingCodes(allMissingCodes, location, category, genderKorean, age, quarter);
//       res.json({
//         code: 202,
//         message: "일부 데이터가 외부 API에서 가져와졌으며 데이터베이스에 저장되었습니다.",
//         data: savedData
//       });
//     } else {
//       res.json({
//         code: 200,
//         message: "모든 관련 데이터를 찾았습니다.",
//         data: nearest
//       });
//     }
//   } catch (error) {
//     console.error('데이터베이스 쿼리 또는 외부 API 호출 중 오류 발생:', error);
//     res.status(500).send('내부 서버 오류');
//   }
// });


module.exports = router;
