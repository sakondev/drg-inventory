$(document).ready(function () {
  $.getJSON("inventory_data.json")
    .done(function (data) {
      $("#lastUpdated").text("Last Updated at: " + data.last_updated);

      // Initialize DataTable
      var table = $("#inventoryTable").DataTable({
        data: [],
        columns: [{ data: "SKU" }, { data: "Item" }, { data: "Qty" }],
        pageLength: -1,
        lengthMenu: [
          [30, 50, 100, -1],
          [30, 50, 100, "All"],
        ],
        paging: true,
        dom: "<'top'lf>irt<'bottom'i<'clear'>p>",

        // Add row callback to change row color based on Qty
        createdRow: function (row, data, dataIndex) {
          if (data.Qty < 5) {
            $(row).addClass("row-critical-qty");
          } else if (data.Qty < 10) {
            $(row).addClass("row-low-qty");
          }
        },
      });

      // Process inventory data
      var processedData = [];
      data.inventory.forEach((item) => {
        var branches = item.Branch;

        // Loop through branches and create entries for each branch
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

      // Add data to DataTable
      table.clear().rows.add(processedData).draw();

      // Populate branch filter checkboxes with unique branch names and assign colors
      var branchNames = {};
      processedData.forEach((item) => {
        branchNames[item.Branch] = true; // Store unique branch names
      });

      // Function to determine branch group based on branch name
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

      // Populate branch checkboxes with group color and check all by default
      Object.keys(branchNames).forEach((branch) => {
        var groupClass = getBranchGroup(branch);
        var checkboxHtml = `
          <label class="branch-checkbox-group ${groupClass}">
            <input type="checkbox" class="branch-checkbox" value="${branch}" checked /> ${branch}
          </label>`;
        $("#branchFilterContainer").append(checkboxHtml);
      });

      // Function to filter and sum by selected branches
      function filterAndUpdateTable() {
        var selectedBranches = [];
        $(".branch-checkbox:checked").each(function () {
          selectedBranches.push($(this).val());
        });

        // Filter data based on selected branches
        var filteredData = processedData.filter((item) =>
          selectedBranches.includes(item.Branch)
        );

        // Group by SKU and sum the quantities
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

        // Convert the grouped data back to an array
        var groupedDataArray = Object.values(groupedData);

        // Update the table with the grouped data
        table.clear().rows.add(groupedDataArray).draw();
      }

      // Trigger the filter and sum function when checkboxes are changed
      $(".branch-checkbox").on("change", filterAndUpdateTable);

      // Select All button functionality
      $("#selectAllButton").on("click", function () {
        $(".branch-checkbox").prop("checked", true);
        filterAndUpdateTable();
      });

      // Deselect All button functionality
      $("#deselectAllButton").on("click", function () {
        $(".branch-checkbox").prop("checked", false);
        filterAndUpdateTable();
      });

      // Trigger the filter function initially to load data with all branches selected
      filterAndUpdateTable();
    })
    .fail(function () {
      console.error("Failed to load JSON data.");
      alert("Error loading data. Please check the console for more details.");
    });

  // Export to Excel with UTF-8 encoding
  $("#exportButton").on("click", function () {
    // Get the table data as JSON
    var tableData = $("#inventoryTable").DataTable().rows().data().toArray();

    // Create a new worksheet from the table
    var ws = XLSX.utils.json_to_sheet(tableData);

    // Apply cell formatting to treat SKU as text
    for (var cell in ws) {
      if (ws.hasOwnProperty(cell) && cell[0] !== "!") {
        // Apply text format to SKU column
        if (cell.startsWith("A")) {
          ws[cell].z = "@"; // '@' format indicates text in Excel
        }
      }
    }

    // Create a new workbook
    var wb = XLSX.utils.book_new();

    // Add the worksheet to the workbook
    XLSX.utils.book_append_sheet(wb, ws, "InventoryData");

    // Export the workbook
    XLSX.writeFile(wb, "inventory_data.xlsx");
  });
});
