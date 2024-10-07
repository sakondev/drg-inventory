$(document).ready(function () {
  let latestFile = "";

  // Function to fetch available JSON files and populate dropdown
  function populateFileDropdown() {
    $.getJSON("data/file_list.json")
      .done(function (files) {
        files.forEach((file) => {
          const datePart = file.split("_")[0];
          const timePart = file.split("_")[1].split(".")[0];

          // Extracting and formatting date and time
          const day = datePart.slice(0, 2);
          const month = datePart.slice(2, 4);
          const year = `20${datePart.slice(4, 6)}`; // Use two last digits to form the year
          const hour = timePart.slice(0, 2);
          const minutes = timePart.slice(2, 4);
          const seconds = timePart.slice(4, 6);

          const formattedDate = `วันที่ ${day}/${month}/${year} ${hour}:${minutes}:${seconds}`;

          $("#fileSelector").append(new Option(formattedDate, file));
        });

        // Set the latest file as the first file in the list
        if (files.length > 0) {
          latestFile = files[0]; // Assuming the first file is the latest
          loadData(latestFile); // Load latest file at startup
        }
      })
      .fail(function () {
        console.error("Failed to load file list.");
      });
  }

  // Load data from the selected file
  function loadData(file) {
    $.getJSON(`data/${file}`)
      .done(function (data) {
        $("#lastUpdated").text("Data Updated at: " + data.last_updated);
        initializeDataTable(data.inventory);
      })
      .fail(function (jqxhr, textStatus, error) {
        const err = textStatus + ", " + error;
        console.error("Failed to load JSON data: " + err);
        alert("Error loading data. Please check the console for more details.");
      });
  }

  // Function to initialize DataTable
  function initializeDataTable(inventory) {
    var processedData = [];
    inventory.forEach((item) => {
      var branches = item.Branch;
      for (var branch in branches) {
        var qty = parseFloat(branches[branch]);
        processedData.push({
          SKU: item.SKU,
          Item: item.Item,
          Branch: branch,
          Qty: qty,
        });
      }
    });

    // Clear any existing DataTable instance
    if ($.fn.dataTable.isDataTable("#inventoryTable")) {
      $("#inventoryTable").DataTable().clear().destroy();
    }

    var table = $("#inventoryTable").DataTable({
      data: processedData,
      columns: [{ data: "SKU" }, { data: "Item" }, { data: "Qty" }],
      pageLength: -1,
      lengthMenu: [
        [30, 50, 100, -1],
        [30, 50, 100, "All"],
      ],
      paging: true,
      dom: "<'top'lf>irt<'bottom'i<'clear'>p>",
      createdRow: function (row, data, dataIndex) {
        if (data.Qty < 5) {
          $(row).addClass("row-critical-qty");
        } else if (data.Qty < 10) {
          $(row).addClass("row-low-qty");
        }
      },
    });

    // Populate branch filter checkboxes
    populateBranchFilter(processedData, table);
  }

  // Function to populate branch filter checkboxes
  function populateBranchFilter(processedData, table) {
    $("#branchFilterContainer").empty(); // Clear existing checkboxes

    var branchNames = {};
    processedData.forEach((item) => {
      branchNames[item.Branch] = true;
    });

    function getBranchGroup(branch) {
      var StoreGroup = [
        "Samyan",
        "Circle",
        "Rama 9",
        "Eastville",
        "Mega",
        "Embassy",
        "EmQuartier",
      ];
      var HqGroup = ["HQ"];
      var OnlineGroup = ["On Time"];
      var VendingGroup = ["True Digital Park", "T One Building"];

      if (StoreGroup.includes(branch)) {
        return "branch-group-store";
      } else if (HqGroup.includes(branch)) {
        return "branch-group-hq";
      } else if (OnlineGroup.includes(branch)) {
        return "branch-group-online";
      } else if (VendingGroup.includes(branch)) {
        return "branch-group-vending";
      }
      return "";
    }

    Object.keys(branchNames).forEach((branch) => {
      var groupClass = getBranchGroup(branch);
      var checkboxHtml = `
        <label class="branch-checkbox-group ${groupClass}">
          <input type="checkbox" class="branch-checkbox" value="${branch}" checked /> ${branch}
        </label>`;
      $("#branchFilterContainer").append(checkboxHtml);
    });

    // Trigger filter and update table
    $(".branch-checkbox").on("change", function () {
      filterAndUpdateTable(processedData, table);
    });

    // Select/Deselect All functionality
    $("#selectAllButton").on("click", function () {
      $(".branch-checkbox").prop("checked", true);
      filterAndUpdateTable(processedData, table);
    });

    $("#deselectAllButton").on("click", function () {
      $(".branch-checkbox").prop("checked", false);
      filterAndUpdateTable(processedData, table);
    });

    // Initial filter
    filterAndUpdateTable(processedData, table);
  }

  // Function to filter and update table
  function filterAndUpdateTable(processedData, table) {
    var selectedBranches = [];
    $(".branch-checkbox:checked").each(function () {
      selectedBranches.push($(this).val());
    });

    var filteredData = processedData.filter((item) =>
      selectedBranches.includes(item.Branch)
    );

    var groupedData = {};
    filteredData.forEach((item) => {
      if (groupedData[item.SKU]) {
        groupedData[item.SKU].Qty += item.Qty;
      } else {
        groupedData[item.SKU] = {
          SKU: item.SKU,
          Item: item.Item,
          Qty: item.Qty,
        };
      }
    });

    table.clear().rows.add(Object.values(groupedData)).draw();
  }

  // Export to Excel with UTF-8 encoding
  $("#exportButton").on("click", function () {
    var tableData = $("#inventoryTable").DataTable().rows().data().toArray();
    var ws = XLSX.utils.json_to_sheet(tableData);
    for (var cell in ws) {
      if (ws.hasOwnProperty(cell) && cell[0] !== "!") {
        if (cell.startsWith("A")) {
          ws[cell].z = "@"; // '@' format indicates text in Excel
        }
      }
    }
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "InventoryData");
    XLSX.writeFile(wb, "inventory_data.xlsx");
  });

  // Populate dropdown for file selection
  populateFileDropdown();

  // Change event for dropdown
  $("#fileSelector").on("change", function () {
    const selectedFile = $(this).val();
    loadData(selectedFile);
  });
});
