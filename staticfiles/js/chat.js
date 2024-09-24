$(function(){

    //console.log(user, room_id)

    var url='ws://' + window.location.host + '/ws/room/' + room_id + '/'

    //console.log(url)

    var chatSocket = new WebSocket(url)
   
    //console.log(chatSocket)
    
    chatSocket.onopen = function(e){
        console.log('WEBSOCKET ABIERTO')
    }

    chatSocket.onclose = function(e){
        console.log('WEBSOCKET CERRADO')
    }

    chatSocket.onmessage = function(e){
        const data = JSON.parse(e.data)

        console.log(data.type)

        if(data.type=='chat_message'){
            const msj = data.message
            const username = data.username
            const datetime = data.datetime

            document.querySelector('#boxMessages').innerHTML +=
            `
            <div class="alert alert-success" role="alert">
                    ${msj}
                    <div>
                        <small class="fst-italic fw-bold">${username}</small>
                        <small class="float-end">${datetime}</small>
                    </div>
            </div>
                `
        }else if(data.type=='user_list'){
            let userListHTML = ''
            let userClass=''

            for(const username of data.users){
                const userClass = (username === user) ? 'list-group-item-success' : ''                
                userListHTML += `<li class="list-group-item ${userClass}">@${username}</li>`
            }
            document.querySelector('#usersList').innerHTML = userListHTML
        
        }else if(data.type=='assigned_manager'){
            const managerName = data.manager_name;
            document.querySelector('#assignedManager').innerText = managerName;
        }
    }

    document.querySelector('#btnMessage').addEventListener('click',
    sendMessage)
    document.querySelector('#inputMessage').addEventListener('keypress',
    function(e){
        if(e.keyCode==13){
            sendMessage()
        }
    })

    function sendMessage(){
        var message = document.querySelector('#inputMessage')

               
        if(message.value.trim() !==''){
            loadMessageHTML(message.value.trim())
            chatSocket.send(JSON.stringify({
                type:'chat_message',
                message: message.value.trim(),
            }))

            console.log(message.value.trim())
            
            message.value=''
        } else{
            console.log('Envió un mensaje vacío')
        }
    }

    function loadMessageHTML(m){
        const dataObject = new Date()
        const year = dataObject.getFullYear()
        const month = dataObject.getMonth() + 1
        const day = dataObject.getDate()
        const hours = dataObject.getHours()
        const minutes = dataObject.getMinutes()
        const seconds = dataObject.getSeconds()

        const formattedDate = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`

        document.querySelector('#boxMessages').innerHTML +=
        `
        <div class="alert alert-primary" role="alert">
                ${m}
                <div>
                    <small class="fst-italic fw-bold">${user}</small>
                    <small class="float-end">${formattedDate}</small>
                </div>
        </div>
            `
    }
});


