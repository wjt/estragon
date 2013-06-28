//  This script and many more from
//   http://rainbow.arch.scriptmania.com

if (document.getElementById){

//   Plenty of black gives a better sparkle effect.

showerCol=new Array('#000000','#ff0000','#ffffff','#000000','#00ff00','#ff00ff','#ffffff','#ffa500','#000000','#fff000');
launchCol=new Array('#ffff00','#ff00ff','#00ffff','#ffffff','#ff8000');
runSpeed=70; //setTimeout speed.

//   *** DO NOT EDIT BELOW ***

var yPos=200;
var xPos=200;
var explosionSize=200;
var launchColour='#ffff80';
var timer=null;
var dims=1;
var evn=360/14;
firework=new Array();
var ieType=(typeof window.innerWidth != 'number');
var ieRef=((ieType) && (document.compatMode) && 
(document.compatMode.indexOf("CSS") != -1))
?document.documentElement:document.body;
thisStep=0;
step=5;

for (i=0; i < 14; i++){
document.write('<div id="sparks'+i+'" style="position:absolute;top:0px;left:0px;height:1px;width:1px;font-size:1px;background-color:'+launchColour+'"><\/div>');
firework[i]=document.getElementById("sparks"+i).style;
}

function winDims(){
winH=(ieType)?ieRef.clientHeight:window.innerHeight; 
winW=(ieType)?ieRef.clientWidth:window.innerWidth;
bestFit=(winW >= winH)?winH:winW;
}
winDims();
window.onresize=new Function("winDims()");

function Reset(){
var dsy=(ieType)?ieRef.scrollTop:window.pageYOffset; 
thisStep=-1;
launchColour = launchCol[Math.floor(Math.random()*launchCol.length)];
explosionSize=Math.round(100+Math.random()*(bestFit/4));
yPos = explosionSize+Math.round(Math.random()*(winH-(explosionSize*2.2)))+dsy;
xPos = explosionSize+Math.round(Math.random()*(winW-(explosionSize*2.2)));
dims=1;
for (i=0; i < 14; i++){
 firework[i].backgroundColor=launchColour;
 firework[i].width=dims+"px";
 firework[i].height=dims+"px";
 firework[i].fontSize=dims+"px";
}
Fireworks();
}

function Fireworks(){
thisStep+=step;
timer=setTimeout("Fireworks()",runSpeed);

for (i=0; i < 14; i++){
firework[i].top = yPos + explosionSize * Math.sin(i*evn*Math.PI/180)*Math.sin(thisStep/100)+"px";
firework[i].left= xPos + explosionSize * Math.cos(i*evn*Math.PI/180)*Math.sin(thisStep/100)+"px";
 if (thisStep > 100){
 dims=(explosionSize < 150)?1:Math.round(1+Math.random()*2);
 firework[i].backgroundColor=showerCol[Math.floor(Math.random()*showerCol.length)];
 firework[i].width=dims+"px";
 firework[i].height=dims+"px";
 firework[i].fontSize=dims+"px";
 }
}
if (thisStep > 160){
 clearTimeout(timer);
 Reset();
}
}

}

