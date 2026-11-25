const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});
    const grammar = b.dependency("grammar", .{
        .target = target,
        .optimize = optimize,
        .@"build-shared" = b.option(bool, "build-shared", "Build a shared library") orelse true,
        .@"reuse-allocator" = b.option(bool, "reuse-allocator", "Reuse the library allocator") orelse false,
    });
    const tests = b.addTest(.{
        .root_module = b.createModule(.{
            .root_source_file = grammar.path("bindings/zig/test.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    tests.root_module.addImport("tree-sitter-zitron", grammar.module("tree-sitter-zitron"));
    tests.root_module.addImport("tree_sitter", b.dependency("tree_sitter", .{
        .target = target,
        .optimize = optimize,
    }).module("tree_sitter"));
    const run_tests = b.addRunArtifact(tests);
    b.step("test", "Run grammar tests").dependOn(&run_tests.step);
}
