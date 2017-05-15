<html>
<head>
<title>Login required</title>
<style>
body{
  padding:0;
  margin:0;
  background: url('{{ background }}');
  background-attachment: fixed;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
}

.vid-container{
  position:relative;
  height:100vh;
  overflow:hidden;
}

.inner-container{
  width:400px;
  height:300px;
  position:absolute;
  top:calc(50vh - 200px);
  left:calc(50vw - 200px);
  overflow:hidden;
}

.box{
  position:absolute;
  height:100%;
  width:100%;
  font-family:Helvetica;
  color:#fff;
  background:rgba(0,0,0,0.4);
  padding:30px 0px;
}

.box h1{
  text-align:center;
  margin:30px 0;
  font-size:30px;
}

.box input{
  display:block;
  width:300px;
  margin:20px auto;
  padding:15px;
  background:rgba(0,0,0,0.2);
  color:#fff;
  border:0;
  font-size:20px;
}
.box input:focus,.box input:active,.box button:focus,.box button:active{
  outline:none;
}
.box button{
  background:#742ECC;
  border:0;
  color:#fff;
  padding:10px;
  font-size:20px;
  width:330px;
  margin:20px auto;
  display:block;
  cursor:pointer;
}
.box button:active{
  background:#27ae60;
}
.box p{
  font-size:14px;
  text-align:center;
}
.box p span{
  cursor:pointer;
  color:#666;
}
</style>
</head>
<body>
<div class="vid-container">
  <div class="inner-container">
    <div class="box">
      <h1>Password protected</h1>
      <form method="post" action="">
          <input type="password" placeholder="Password" name="password"/>
          <button type="submit">Go !</button>
      </form>
    </div>
  </div>
</div>
</body>
</html>
