from typing import Optional, Sequence
import os
import json
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import tempfile

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1beta3 as documentai

# Configuration
project_id = "gen-lang-client-0849825641"
location = "us"
processor_id = "6af87434352688a1"
processor_version = "rc"
file_path = "sample.png"
mime_type = "application/pdf"


def process_document_layout_parser_sample(
    project_id: str,
    location: str,
    processor_id: str,
    processor_version: str,
    file_path: str,
    mime_type: str,
) -> None:
    # Layout Parser specific configurations
    process_options = documentai.ProcessOptions(
        layout_config=documentai.ProcessOptions.LayoutConfig(
            chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                chunk_size=500,
                include_ancestor_headings=True
            ),
            return_images=True,
            return_bounding_boxes=True,
            enable_image_annotation=False,
            enable_image_extraction=True,
            enable_table_annotation=False,
            enable_llm_layout_parsing=False,
        )
    )
    
    # Convert image to PDF if needed
    if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        pdf_path = convert_image_to_pdf(file_path)
        mime_type = "application/pdf"
    else:
        pdf_path = file_path
    
    # Process document with Layout Parser
    document = process_document(
        project_id,
        location,
        processor_id,
        processor_version,
        pdf_path,
        mime_type,
        process_options=process_options,
    )

    text = document.text
    print(f"Full document text: {repr(text)}\n")
    print(f"There are {len(document.pages)} page(s) in this document.\n")

    # Layout Parser specific results
    print_layout_blocks(document)
    print_chunks(document)
    print_images(document)
    
    # Save results to JSON
    save_results_to_json(document, file_path)
    
    # Clean up temporary file
    if pdf_path != file_path and os.path.exists(pdf_path):
        os.unlink(pdf_path)
        print(f"🧹 Cleaned up temporary file: {pdf_path}")


def convert_image_to_pdf(image_path: str) -> str:
    """Convert image to PDF for Layout Parser processing"""
    img = Image.open(image_path)
    temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    img_width, img_height = img.size
    pdf_width, pdf_height = A4
    
    if img_width > img_height:
        pdf_height = pdf_width * img_height / img_width
    else:
        pdf_width = pdf_height * img_width / img_height
    
    c = canvas.Canvas(temp_pdf_path, pagesize=(pdf_width, pdf_height))
    c.drawImage(image_path, 0, 0, width=pdf_width, height=pdf_height)
    c.save()
    
    print(f"✅ Image converted: {image_path} → PDF ({img_width}x{img_height}px)")
    return temp_pdf_path


def print_layout_blocks(document: documentai.Document) -> None:
    """Print layout blocks from document_layout"""
    if hasattr(document, 'document_layout') and document.document_layout:
        blocks = document.document_layout.blocks
        print(f"Layout blocks detected: {len(blocks)}")
        
        for i, block in enumerate(blocks, 1):
            if hasattr(block, 'text_block') and block.text_block and block.text_block.text:
                text = block.text_block.text.strip()
                print(f"    Block {i}: {repr(text)}")
            
            if hasattr(block, 'image_block') and block.image_block:
                if hasattr(block.image_block, 'blob_asset_id') and block.image_block.blob_asset_id:
                    print(f"    Block {i}: Image block (blob_asset_id: {block.image_block.blob_asset_id})")
    else:
        print("No document_layout blocks found")


def print_chunks(document: documentai.Document) -> None:
    """Print chunked document results"""
    if hasattr(document, 'chunked_document') and document.chunked_document:
        chunks = document.chunked_document.chunks
        print(f"\nChunks detected: {len(chunks)}")
        
        for i, chunk in enumerate(chunks, 1):
            chunk_text = chunk.content.strip()
            print(f"    Chunk {i} ({len(chunk_text)} chars): {repr(chunk_text[:100])}")
            if len(chunk_text) > 100:
                print(f"        ... (truncated)")
    else:
        print("\nNo chunks found")


def print_images(document: documentai.Document) -> None:
    """Print and save images"""
    if hasattr(document, 'pages') and document.pages:
        print(f"\nImages processing:")
        
        for page_idx, page in enumerate(document.pages, 1):
            if hasattr(page, 'image') and page.image:
                try:
                    # Extract image data
                    if hasattr(page.image, 'content') and page.image.content:
                        image_data = page.image.content
                    elif hasattr(page.image, 'data') and page.image.data:
                        image_data = page.image.data
                    else:
                        image_data = page.image
                    
                    # Save image
                    os.makedirs("extracted_images", exist_ok=True)
                    image_filename = f"extracted_images/layout_page_{page_idx}.png"
                    
                    with open(image_filename, "wb") as f:
                        f.write(image_data)
                    
                    print(f"    Page {page_idx} image saved: {image_filename} ({len(image_data):,} bytes)")
                    
                except Exception as e:
                    print(f"    Page {page_idx} image extraction failed: {e}")
    
    # Extract blob_assets
    if hasattr(document, 'blob_assets') and document.blob_assets:
        print(f"Blob assets found: {len(document.blob_assets)}")
        
        for blob_asset in document.blob_assets:
            blob_filename = f"extracted_images/blob_{blob_asset.name}.png"
            with open(blob_filename, "wb") as f:
                f.write(blob_asset.data)
            
            print(f"    Blob asset saved: {blob_filename} ({len(blob_asset.data):,} bytes)")


def save_results_to_json(document: documentai.Document, input_file: str) -> None:
    """Save processing results to JSON file"""
    results = {
        "input_file": input_file,
        "full_document_text": document.text,
        "pages_count": len(document.pages),
        "layout_blocks": [],
        "chunks": [],
        "images_info": []
    }
    
    # Layout blocks
    if hasattr(document, 'document_layout') and document.document_layout:
        for i, block in enumerate(document.document_layout.blocks, 1):
            block_info = {"block_id": i}
            if hasattr(block, 'text_block') and block.text_block and block.text_block.text:
                block_info["type"] = "text"
                block_info["content"] = block.text_block.text.strip()
            elif hasattr(block, 'image_block') and block.image_block:
                block_info["type"] = "image"
                if hasattr(block.image_block, 'blob_asset_id') and block.image_block.blob_asset_id:
                    block_info["blob_asset_id"] = block.image_block.blob_asset_id
            results["layout_blocks"].append(block_info)
    
    # Chunks
    if hasattr(document, 'chunked_document') and document.chunked_document:
        for i, chunk in enumerate(document.chunked_document.chunks, 1):
            chunk_info = {
                "chunk_id": i,
                "content": chunk.content.strip(),
                "char_count": len(chunk.content.strip())
            }
            results["chunks"].append(chunk_info)
    
    # Images info
    if hasattr(document, 'pages') and document.pages:
        for page_idx, page in enumerate(document.pages, 1):
            if hasattr(page, 'image') and page.image:
                try:
                    if hasattr(page.image, 'content') and page.image.content:
                        image_data = page.image.content
                    elif hasattr(page.image, 'data') and page.image.data:
                        image_data = page.image.data
                    else:
                        image_data = page.image
                    
                    image_info = {
                        "page": page_idx,
                        "size_bytes": len(image_data),
                        "saved_filename": f"extracted_images/layout_page_{page_idx}.png"
                    }
                    results["images_info"].append(image_info)
                except Exception as e:
                    error_info = {
                        "page": page_idx,
                        "error": str(e)
                    }
                    results["images_info"].append(error_info)
    
    # Blob assets
    if hasattr(document, 'blob_assets') and document.blob_assets:
        for blob_asset in document.blob_assets:
            blob_info = {
                "name": blob_asset.name,
                "size_bytes": len(blob_asset.data),
                "saved_filename": f"extracted_images/blob_{blob_asset.name}.png"
            }
            results["images_info"].append(blob_info)
    
    # Save to JSON
    output_file = "layout_parser_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")


def process_document(
    project_id: str,
    location: str,
    processor_id: str,
    processor_version: str,
    file_path: str,
    mime_type: str,
    process_options: Optional[documentai.ProcessOptions] = None,
) -> documentai.Document:
    # You must set the `api_endpoint` if you use a location other than "us".
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(
            api_endpoint=f"{location}-documentai.googleapis.com"
        )
    )

    # The full resource name of the processor version
    name = client.processor_version_path(
        project_id, location, processor_id, processor_version
    )

    # Read the file into memory
    with open(file_path, "rb") as image:
        image_content = image.read()

    # Configure the process request
    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(content=image_content, mime_type=mime_type),
        process_options=process_options,
    )

    result = client.process_document(request=request)
    
    # Save raw result object to JSON
    try:
        # Convert result to dict for JSON serialization
        from google.protobuf.json_format import MessageToDict
        result_dict = MessageToDict(result._pb)
        
        with open("raw_result.json", 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Raw result object saved to: raw_result.json")
        print(f"🔍 Result type: {type(result)}")
        print(f"📊 Result attributes: {list(dir(result))}")
    except Exception as e:
        print(f"❌ Could not save raw result: {e}")
    
    return result.document


def layout_to_text(layout: documentai.Document.Page.Layout, text: str) -> str:
    """
    Document AI identifies text in different parts of the document by their
    offsets in the entirety of the document's text. This function converts
    offsets to a string.
    """
    if not layout.text_anchor or not layout.text_anchor.text_segments:
        return ""
    
    return "".join(
        text[int(segment.start_index) : int(segment.end_index)]
        for segment in layout.text_anchor.text_segments
    )


if __name__ == "__main__":
    print("🔍 Layout Parser Simple Test")
    print("=" * 50)
    
    process_document_layout_parser_sample(
        project_id=project_id,
        location=location,
        processor_id=processor_id,
        processor_version=processor_version,
        file_path=file_path,
        mime_type=mime_type,
    )
    
    print("\n✅ Layout Parser test completed")