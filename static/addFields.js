function addFields(){
  var number = document.getElementById("filesnum").value;
  var container = document.getElementById("fieldscontainer");
  while (container.hasChildNodes()) {
      container.removeChild(container.lastChild);
  }
  var form = document.createElement("form");
  form.method = "post";
  form.enctype = "multipart/form-data";
  container.appendChild(form);
  container.appendChild(document.createElement("br"));
  for (i=0;i<number;i++){
      container.appendChild(document.createTextNode("File " + (i+1)));
      var input = document.createElement("input");
      input.type = "file";
      input.name = "file" + i;
      container.appendChild(input);
      container.appendChild(document.createElement("br"));
  }
  var input = document.createElement("input");
  input.type = "submit";
  input.value = "Upload"; 
  container.appendChild(input);
  container.appendChild(document.createElement("br"));
}
