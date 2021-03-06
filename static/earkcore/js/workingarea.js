/**
 * Preview file
 */
function previewfile(node) {
    if(node.data) {
        var ip_work_dir_sub_path = node.data.path;
        var mimetype = node.data.mimetype;
        var url = "/earkweb/earkcore/read_ipfc/" + ip_work_dir_sub_path;

        window.open(url,'file view','directories=no,titlebar=no,toolbar=no,location=no,status=no,menubar=no,scrollbars=no,resizable=yes,width=1000,height=800');

    }
 }

function isEAD(name) {
    return !!(name.toLowerCase().match(/ead[A-Za-z0-9-_]{0,20}.xml/));
}

function isStateXML(name) {
    return !!(name.toLowerCase().match(/state.xml/));
}

function previewSupported(name) {
    return !!(name.toLowerCase().match(/(.pdf$|.png$|.xml$|.png$|.log$|.xsd|.txt$)/));
}

/**
 * Context menu
 */
function customMenu(node) {

    var items = {
        viewItem: {
            label: "View",
            action: function () { previewfile(node); }
        },
        editItem: {
            label: "Edit",
            action: function () { window.location.href = '/earkweb/earkcore/xmleditor/'+ node.data.path +'/'; }
        }
    };
    var n = $(node)[0];
    if (!isEAD(n.text) && !isStateXML(n.text)) { delete items.editItem; }
    if (!previewSupported(n.text)) { delete items.viewItem; }
    return items;
}


/**
 * Populate tree using json representation of the directory hierarchy
 * (variable 'uuid' is provided as global variable)
 */
(function(){
    $.ajax({
        url: "/earkweb/earkcore/get_directory_json",
        type: "POST",
        data: "uuid="+uuid,
    }).success(function(dir_as_json){
        $('#directorytree')
        .on('open_node.jstree', function (e, data) {
            $('#directorytree').jstree(true).set_icon(data.node.id, 'glyphicon glyphicon-folder-open');
         }).on('close_node.jstree', function (e, data) {
            $('#directorytree').jstree(true).set_icon(data.node.id, 'glyphicon glyphicon-folder-close');
         }).on('move_node.jstree', function (e, data) {
            origin_path = data.node.data.path;
            target_path = $('#directorytree').jstree().get_node(data.parent).data.path;
            console.log("Original path: "+origin_path);
            console.log("Target path: "+target_path);
         }).on('dblclick.jstree', function (e) {
            var node = $('#directorytree').jstree(true).get_node(e.target);
            if(previewSupported(node.data.path)) {
                previewfile(node);
            } else {
                alert("Preview of this file type is not supported!");
            }
         }).on('loaded.jstree', function() {
            $('#directorytree').jstree('open_all');
         }).jstree({ 'core' : dir_as_json, "plugins" : [
            //"checkbox",
            "contextmenu",
            "dnd",
            //"massload",
            //"search",
            //"sort",
            //"state",
            //"types",
            //"unique",
            //"wholerow",
            "changed",
            //"conditionalselect"
        ], contextmenu: {items: customMenu} });
        $(document).on('dnd_start.vakata', function (e, data) {
            console.log(data);
        });
    });
})();
