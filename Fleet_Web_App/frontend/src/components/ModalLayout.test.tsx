import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ModalBody, ModalFooter, ModalPanel, ModalViewport } from './ModalLayout'

describe('ModalLayout', () => {
  it('keeps the panel within the dynamic viewport and its footer visible', () => {
    render(<ModalViewport><ModalPanel><ModalBody>Content</ModalBody><ModalFooter>Actions</ModalFooter></ModalPanel></ModalViewport>)

    expect(screen.getByTestId('modal-panel')).toHaveClass('max-h-[calc(100dvh-3rem)]', 'overflow-hidden')
    expect(screen.getByText('Content')).toHaveClass('overflow-y-auto')
    expect(screen.getByText('Actions')).toHaveClass('shrink-0')
  })
})
