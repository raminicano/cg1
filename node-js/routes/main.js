
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
  const { location, inquiry_time } = req.query;
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
      [closestLandmark, inquiry_time]
    );

    console.log(inquiry_time);

    if (rows.length > 0) {
      res.json(rows);
    } else {
      // 데이터가 없을 경우 외부 API 호출
      await axios.get('http://localhost:3000/location/congestion', {
        params: { location, input_time: inquiry_time }
      });

      // 다시 데이터 조회
      const [newRows] = await pool.query(
        'SELECT * FROM congestion WHERE area_nm = ? AND inquiry_time = ?',
        [closestLandmark, inquiry_time]
      );

      res.json(newRows);
    }
  } catch (error) {
    console.error('Error during database query or API call', error);
    res.status(500).send('Internal Server Error');
  }
});

module.exports = router;
