const express = require('express')
const morgan = require('morgan')
const path = require('path')
const app = express()
const bodyParser = require('body-parser')
// const cookieParser = require('cookie-parser')
app.set('view engine', 'ejs');  // EJS를 뷰 엔진으로 설정
app.set('views', './public');    // 뷰 파일 경로 설정



app.set('port', process.env.PORT || 8000)
app.use(morgan('dev'))
app.use(bodyParser.json())
app.use(bodyParser.urlencoded({ extended: false }))
// app.use(cookieParser())
app.use(express.static(path.join(__dirname, 'public')))

var main = require('./routes/main.js')
app.use('/', main)

app.listen(app.get('port'), () => {
    console.log('8000 Port: Server Started~!!')
});


