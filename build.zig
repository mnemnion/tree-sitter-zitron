const std = @import("std");

pub fn build(b: *std.Build) !void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const shared = b.option(bool, "build-shared", "Build a shared library") orelse true;
    const reuse_alloc = b.option(bool, "reuse-allocator", "Reuse the library allocator") orelse false;

    const library_name = "tree-sitter-zitron";

    const lib: *std.Build.Step.Compile = b.addLibrary(.{
        .name = library_name,
        .linkage = if (shared) .dynamic else .static,
        .root_module = b.createModule(.{
            .target = target,
            .optimize = optimize,
            .link_libc = true,
            .pic = if (shared) true else null,
        }),
    });

    lib.root_module.addCSourceFile(.{
        .file = b.path("src/parser.c"),
        .flags = &.{"-std=c11"},
    });
    if (fileExists(b, "src/scanner.c")) {
        lib.root_module.addCSourceFile(.{
            .file = b.path("src/scanner.c"),
            .flags = &.{"-std=c11"},
        });
    }

    if (reuse_alloc) {
        lib.root_module.addCMacro("TREE_SITTER_REUSE_ALLOCATOR", "");
    }
    if (optimize == .debug) {
        lib.root_module.addCMacro("TREE_SITTER_DEBUG", "");
    }

    lib.root_module.addIncludePath(b.path("src"));

    b.installArtifact(lib);
    b.installFile("src/node-types.json", "node-types.json");

    if (fileExists(b, "queries")) {
        b.installDirectory(.{
            .source_dir = b.path("queries"),
            .install_dir = .prefix,
            .install_subdir = "queries",
            .include_extensions = &.{"scm"},
        });
    }

    const module = b.addModule(library_name, .{
        .root_source_file = b.path("bindings/zig/root.zig"),
        .target = target,
        .optimize = optimize,
    });
    module.linkLibrary(lib);

    const run_tests = std.Build.Step.Run.create(b, "grammar tests");
    run_tests.addFileArg2(.zig_exe, .{});
    run_tests.addArgs(&.{ "build", "test" });
    run_tests.setCwd(b.path("tests"));
    run_tests.addArg(b.fmt("-Doptimize={s}", .{@tagName(optimize)}));
    run_tests.addArg(b.fmt("-Dtarget={s}", .{target.query.zigTriple(b.allocator) catch @panic("OOM")}));
    run_tests.addArg(b.fmt("-Dcpu={s}", .{target.query.serializeCpuAlloc(b.allocator) catch @panic("OOM")}));
    run_tests.addArg(b.fmt("-Dbuild-shared={}", .{shared}));
    run_tests.addArg(b.fmt("-Dreuse-allocator={}", .{reuse_alloc}));
    run_tests.has_side_effects = true;
    b.step("test", "Run unit tests").dependOn(&run_tests.step);
}

inline fn fileExists(b: *std.Build, filename: []const u8) bool {
    const io = b.graph.io;
    b.dependOnDirectoryContents(b.path(std.fs.path.dirname(filename) orelse "."));
    const dir = b.root;
    dir.access(io, filename, .{}) catch return false;
    return true;
}
