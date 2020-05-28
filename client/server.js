const http = require("http");
const bodyParser = require('body-parser');
const express = require('express');
const WebSocket = require('ws');
const redis = require('redis');
const path = require('path');
const engines = require('consolidate');
redisPort = process.env.REDIS_PORT || 6379,
redisHost = process.env.REDIS_HOST || 'localhost',
reidsPassword = process.env.REDIS_PASSWORD,
redisClient = redis.createClient({port:redisPort, host: redisHost, password: reidsPassword}),
WebSocketServer = WebSocket.Server,
app = express(),
server = http.createServer(app),
port = process.env.PORT || 3000,
streamName = process.env.STREAM || 'camera:0';
// var engines = require('consolidate');
app.use(bodyParser.json());
// app.use(express.static('public'));
app.use(express.static(path.join(__dirname, 'public')));
app.set('views', path.join(__dirname, 'views'));
const hbs = require('hbs');
app.set('view engine','hbs');



app.get('/', function(req, res){
   res.render('scan.hbs');
});
// app.get('/', function(req, res){
//    res.render('home.hbs');
// });

app.post('/image', function (req, res) {
	wss.clients.forEach(function each(client) {
		if (client.readyState === WebSocket.OPEN) {
			client.send(req.body.image);
		}
	});
	res.send('OK');
});


var readStream = function(){
	redisClient.xread('Block', 10000000, 'STREAMS', 'results', '$',  function (err, stream) {
		readStream();
		if(err){
			return console.error(err);
		}
		// var image = stream[0][1][0][1][1];
        var image = stream[0][1][0][1][3];
		// console.log(image);
		wss.clients.forEach(function each(client) {
        		if (client.readyState === WebSocket.OPEN) {
        			client.send(image);
		        }
	        });
	});
};

readStream();

server.listen(port, () => console.log(`Redisafe - app listening on port ${port}!`));

const wss = new WebSocketServer({server: server});

wss.on('connection', function (ws) {
	ws.on('message', function (message) {
		console.log('received: %s', message)
	});
});
