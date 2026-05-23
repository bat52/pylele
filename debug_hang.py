#!/usr/bin/env python3

"""
Test to isolate where the hang occurs: generation vs export/volume check
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_generation_only():
    """Test just the generation phase without export"""
    print("Testing generation only for all_assembly with build123d...")
    
    try:
        from pylele.pylele2.all_assembly import LeleAllAssembly
        
        # Create assembly instance
        assembly = LeleAllAssembly()
        
        # Manually set up CLI for build123d
        from argparse import Namespace
        from b13d.api.core import Implementation, Fidelity
        
        assembly.cli = Namespace(
            implementation=Implementation.BUILD123D,
            fidelity=Fidelity.LOW,
            is_cut=False,
            outdir='.',
            section_x=[-1000, 1000],
            section_y=[-1000, 1000],
            section_z=[-1000, 1000],
            stl_check_en=False,  # Disable volume checking for now
            reference_volume=None,
            reference_volume_tolerance=10,
            export=None,
            show_strings=False,
            show_tuners=False,
            separate_top=False,
            separate_bottom=False,
            separate_neck=False,
            separate_fretboard=False,
            separate_bridge=False,
            all=False,
            all_distance=0.0,
            scale_length=25.5,
            nutWth=43.0,
            fretboard_rise_angle=0.0,
            fret_type='round'
        )
        
        # Configure the API
        assembly.configure()
        
        print("Starting generation...")
        start_time = time.time()
        
        # Generate the shape
        shape = assembly.gen_full()
        
        end_time = time.time()
        
        print(f"Generation completed in {end_time - start_time:.2f} seconds")
        print(f"Shape generated: {shape is not None}")
        
        if shape is not None:
            print(f"Shape type: {type(shape)}")
            if hasattr(shape, 'solid'):
                print(f"Solid type: {type(shape.solid)}")
                if shape.solid is not None:
                    # Try to get volume using build123d's own method
                    try:
                        volume = shape.solid().volume
                        print(f"Build123d volume: {volume}")
                    except:
                        print("Could not get volume from build123d solid")
            
        return shape is not None
        
    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_export_no_volume_check():
    """Test generation and export but disable volume checking"""
    print("\nTesting generation + export (no volume check) for all_assembly with build123d...")
    
    try:
        from pylele.pylele2.all_assembly import LeleAllAssembly
        
        # Create assembly instance
        assembly = LeleAllAssembly()
        
        # Manually set up CLI for build123d
        from argparse import Namespace
        from b13d.api.core import Implementation, Fidelity
        
        assembly.cli = Namespace(
            implementation=Implementation.BUILD123D,
            fidelity=Fidelity.LOW,
            is_cut=False,
            outdir='./test_output',
            section_x=[-1000, 1000],
            section_y=[-1000, 1000],
            section_z=[-1000, 1000],
            stl_check_en=False,  # Disable volume checking for now
            reference_volume=None,
            reference_volume_tolerance=10,
            export=None,
            show_strings=False,
            show_tuners=False,
            separate_top=False,
            separate_bottom=False,
            separate_neck=False,
            separate_fretboard=False,
            separate_bridge=False,
            all=False,
            all_distance=0.0,
            scale_length=25.5,
            nutWth=43.0,
            fretboard_rise_angle=0.0,
            fret_type='round'
        )
        
        # Create output directory
        os.makedirs('./test_output', exist_ok=True)
        
        # Configure the API
        assembly.configure()
        
        print("Starting generation and export...")
        start_time = time.time()
        
        # Generate and export
        output_file = assembly.export_stl()
        
        end_time = time.time()
        
        print(f"Export completed in {end_time - start_time:.2f} seconds")
        print(f"Output file: {output_file}")
        
        if output_file and os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"STL file size: {size} bytes")
            return True
        else:
            print("Export failed - no output file")
            return False
        
    except Exception as e:
        print(f"Error during generation/export: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ISOLATING THE HANG: GENERATION vs EXPORT/VOLUME CHECK")
    print("=" * 60)
    
    # Test 1: Generation only
    gen_success = test_generation_only()
    
    # Test 2: Generation + export (no volume check)
    export_success = test_with_export_no_volume_check()
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print(f"Generation only: {'SUCCESS' if gen_success else 'FAILED'}")
    print(f"Generation + export (no vol check): {'SUCCESS' if export_success else 'FAILED'}")
    print("=" * 60)
    
    if gen_success and not export_success:
        print("ISSUE ISOLATED: Problem occurs during export or volume checking")
    elif not gen_success:
        print("ISSUE ISOLATED: Problem occurs during generation")
    else:
        print("Both generation and export work - issue may be elsewhere")
