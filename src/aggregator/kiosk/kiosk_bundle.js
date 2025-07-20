function main(cfg) {
    let network_api = new NetworkAPI(cfg);

    // network_api.open_websocket();

    network_api.fetch_space_state()
        .then(state => {
            console.log(state);
        })
        .catch(error => {
            console.log('Error fetching space state', error);
        });
}


class NetworkAPI {
    constructor(cfg) {
        this.space_state_url = cfg.space_state_url;
        this.websocket_uri = build_websocket_uri(cfg.websockets_url_path);
        let urlParams = new URLSearchParams(window.location.search);
        this.space_state_username = urlParams.get('username');
        this.space_state_password = urlParams.get('password');
    }

    fetch_space_state() {
        let headers = new Headers();
        headers.set('Authorization', 'Basic ' + btoa(this.space_state_username + ":" + this.space_state_password));
        return fetch(this.space_state_url, {
            method: 'GET',
            headers: headers,
        }).then(response => {
            if (response.status !== 200) {
                throw new Error(`Unexpected HTTP status ${response.status}`);
            } else {
                return response.json();
            }
        });
    }

    open_websocket() {
        let socket = new WebSocket(this.websocket_uri);

        // Handle any errors that occur.
        socket.onerror = function(error) {
            console.log('WebSocket Error', error);
        };

        // Show a connected message when the WebSocket is opened.
        socket.onopen = function(event) {
            console.log('Connected', event.currentTarget.url);
        };

        // Handle messages sent by the server.
        socket.onmessage = function(event) {
            console.log('Message', event.data);
        };

        // Show a disconnected message when the WebSocket is closed.
        socket.onclose = function(event) {
            console.log('Disconnected from WebSocket.');
        };
    }
}


function build_websocket_uri(websocket_path) {
    let loc = window.location, ws_uri;
    if (loc.protocol === "https:") {
        ws_uri = "wss:";
    } else {
        ws_uri = "ws:";
    }
    ws_uri += "//" + loc.host + websocket_path;
    return ws_uri;
}
