var settings = {
    groupDataArray: (typeof groupDataArray !== "undefined") ? groupDataArray : '',
    groupItemName: "groupName",
    groupArrayName: "groupData",
    itemName: "city",
    valueName: "value",
    callable: function (items) {
        console.dir(items);
    },
};

$("#transfer3").transfer(settings);
